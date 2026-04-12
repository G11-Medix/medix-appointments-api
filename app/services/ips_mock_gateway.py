from datetime import date, datetime
from typing import Any

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
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

    def list_specialties(self, route: IpsRoute) -> list[dict[str, Any]]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/especialidades",
        )
        return response if isinstance(response, list) else []

    def get_current_ips(self, route: IpsRoute) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/ips/actual",
        )
        return response if isinstance(response, dict) else {}

    def list_providers(self, route: IpsRoute, id_especialidad: int | None = None) -> list[dict[str, Any]]:
        params = {"id_especialidad": id_especialidad} if id_especialidad is not None else None
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/prestadores",
            params=params,
        )
        return response if isinstance(response, list) else []

    def get_provider_slots(
        self,
        route: IpsRoute,
        id_prestador: int,
        fecha: date,
    ) -> list[dict[str, Any]]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/prestadores/{id_prestador}/cupos",
            params={"fecha": fecha.isoformat()},
        )
        return response if isinstance(response, list) else []

    def create_appointment(
        self,
        route: IpsRoute,
        id_paciente: int,
        id_prestador: int,
        fecha_hora_cupo: datetime,
    ) -> dict[str, Any]:
        response = self._client().request(
            method="POST",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/citas",
            payload={
                "id_paciente": id_paciente,
                "id_prestador": id_prestador,
                "fecha_hora_cupo": fecha_hora_cupo.isoformat(),
            },
        )
        return response if isinstance(response, dict) else {}

    def cancel_appointment(self, route: IpsRoute, id_cita: int, motivo: str | None) -> dict[str, Any]:
        response = self._client().request(
            method="PATCH",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/citas/{id_cita}/cancelar",
            payload={"motivo": motivo},
        )
        return response if isinstance(response, dict) else {}

    def reschedule_appointment(
        self,
        route: IpsRoute,
        id_cita: int,
        nueva_fecha_hora_cupo: datetime,
    ) -> dict[str, Any]:
        response = self._client().request(
            method="PATCH",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/citas/{id_cita}/reprogramar",
            payload={"nueva_fecha_hora_cupo": nueva_fecha_hora_cupo.isoformat()},
        )
        return response if isinstance(response, dict) else {}

    def find_patient_by_document(
        self,
        route: IpsRoute,
        tipo_documento: str,
        numero_documento: str,
    ) -> dict[str, Any]:
        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/pacientes/{tipo_documento}/{numero_documento}",
        )
        return response if isinstance(response, dict) else {}

    def _settings(self) -> Settings:
        if self.settings is None:
            self.settings = get_settings()
        return self.settings

    def _client(self) -> IpsClient:
        if self.client is None:
            self.client = IpsClient(timeout_seconds=self._settings().ips_timeout_seconds)
        return self.client
