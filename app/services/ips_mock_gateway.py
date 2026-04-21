from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.services.fhir_interop import (
    appointment_to_legacy,
    build_appointment_resource,
    build_cancel_patch,
    build_reschedule_patch,
    bundle_entries,
    document_identifier_system,
    fhir_headers,
    first_bundle_resource,
    organization_to_legacy,
    patient_to_legacy,
    practitioner_role_to_legacy,
    slot_to_legacy,
    specialty_from_codeable_concepts,
)
from app.services.ips_route_resolver import IpsRoute, IpsRouteResolver


class IpsMockGateway:
    def __init__(
        self,
        client: IpsClient | None = None,
        settings: Settings | None = None,
        route_resolver: IpsRouteResolver | None = None,
    ) -> None:
        self.client = client
        self.settings = settings
        self.route_resolver = route_resolver or IpsRouteResolver(settings=settings)

    def list_routes(self) -> list[IpsRoute]:
        return self.route_resolver.list_routes()

    def get_route(self, id_institucion: int) -> IpsRoute:
        return self.route_resolver.get_route(id_institucion)

    def list_specialties(self, route: IpsRoute, access_token: str | None = None) -> list[dict[str, Any]]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/PractitionerRole",
            params=None,
            extra_headers=fhir_headers(),
        )
        specialties: dict[int, str] = {}
        for resource in bundle_entries(response):
            specialty_id, specialty_name = specialty_from_codeable_concepts(resource.get("specialty") or [])
            if specialty_id is not None and specialty_name:
                specialties[specialty_id] = specialty_name
        return [{"id": specialty_id, "nombre": name} for specialty_id, name in specialties.items()]

    def get_current_ips(self, route: IpsRoute, access_token: str | None = None) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/Organization",
            extra_headers=fhir_headers(),
        )
        resource = first_bundle_resource(response)
        return organization_to_legacy(resource) if resource else {}

    def list_providers(
        self,
        route: IpsRoute,
        id_especialidad: int | None = None,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if id_especialidad is not None:
            params["specialty"] = id_especialidad
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/PractitionerRole",
            params=params,
            extra_headers=fhir_headers(),
        )
        return [practitioner_role_to_legacy(resource) for resource in bundle_entries(response)]

    def get_provider_slots(
        self,
        route: IpsRoute,
        id_prestador: int,
        fecha: date,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/Slot",
            params={"schedule": f"Schedule/{id_prestador}", "start": fecha.isoformat()},
            extra_headers=fhir_headers(access_token),
        )
        return [slot_to_legacy(resource) for resource in bundle_entries(response)]

    def create_appointment(
        self,
        route: IpsRoute,
        id_paciente: int,
        id_prestador: int,
        fecha_hora_cupo: datetime,
        id_especialidad: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        provider_rows = self.list_providers(route, id_especialidad=id_especialidad, access_token=access_token)
        provider_row = next((row for row in provider_rows if int(row["id"]) == id_prestador), None)
        response = self._client().request(
            method="POST",
            base_url=route.base_url,
            path="/fhir/Appointment",
            payload=build_appointment_resource(
                patient_id=id_paciente,
                provider_id=id_prestador,
                specialty_id=int(provider_row["id_especialidad"]) if provider_row else 0,
                specialty_name=str(provider_row.get("nombre_especialidad") or "") if provider_row else None,
                slot_start=fecha_hora_cupo,
            ),
            extra_headers=fhir_headers(access_token),
        )
        return appointment_to_legacy(response) if isinstance(response, dict) else {}

    def cancel_appointment(
        self,
        route: IpsRoute,
        id_cita: int,
        motivo: str | None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        response = self._client().request(
            method="PATCH",
            base_url=route.base_url,
            path=f"/fhir/Appointment/{id_cita}",
            payload=build_cancel_patch(motivo),
            extra_headers=fhir_headers(access_token),
        )
        return appointment_to_legacy(response) if isinstance(response, dict) else {}

    def reschedule_appointment(
        self,
        route: IpsRoute,
        id_cita: int,
        nueva_fecha_hora_cupo: datetime,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_appointment(route, id_cita, access_token=access_token)
        response = self._client().request(
            method="PATCH",
            base_url=route.base_url,
            path=f"/fhir/Appointment/{id_cita}",
            payload=build_reschedule_patch(
                provider_id=int(existing["id_prestador"]),
                specialty_id=int(existing["id_especialidad"]),
                specialty_name=None,
                slot_start=nueva_fecha_hora_cupo,
            ),
            extra_headers=fhir_headers(access_token),
        )
        return appointment_to_legacy(response) if isinstance(response, dict) else {}

    def find_patient_by_document(
        self,
        route: IpsRoute,
        tipo_documento: str,
        numero_documento: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/Patient",
            params={"identifier": f"{document_identifier_system(tipo_documento)}|{numero_documento}"},
            extra_headers=fhir_headers(),
        )
        patient_resources = bundle_entries(response)
        if not patient_resources:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
        return patient_to_legacy(patient_resources[0])

    def get_patient(self, route: IpsRoute, id_paciente: int, access_token: str | None = None) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path=f"/fhir/Patient/{id_paciente}",
            extra_headers=fhir_headers(),
        )
        return patient_to_legacy(response) if isinstance(response, dict) else {}

    def get_appointment(self, route: IpsRoute, id_cita: int, access_token: str | None = None) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path=f"/fhir/Appointment/{id_cita}",
            extra_headers=fhir_headers(access_token),
        )
        return appointment_to_legacy(response) if isinstance(response, dict) else {}

    def list_appointments(
        self,
        route: IpsRoute,
        *,
        id_paciente: int | None = None,
        desde: datetime | None = None,
        estado: str | None = None,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if id_paciente is not None:
            params["patient"] = f"Patient/{id_paciente}"
        if desde is not None:
            params["date"] = desde.date().isoformat()
        if estado is not None:
            params["status"] = "booked" if estado == "scheduled" else estado
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            path="/fhir/Appointment",
            params=params or None,
            extra_headers=fhir_headers(access_token),
        )
        return [appointment_to_legacy(resource) for resource in bundle_entries(response)]

    def _settings(self) -> Settings:
        if self.settings is None:
            self.settings = get_settings()
        return self.settings

    def _client(self) -> IpsClient:
        if self.client is None:
            self.client = IpsClient(timeout_seconds=self._settings().ips_timeout_seconds)
        return self.client
