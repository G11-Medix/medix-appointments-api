from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any


SPECIALTY_SYSTEM = "urn:medix:specialty"


def fhir_headers(access_token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def bundle_entries(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return []
    result: list[dict[str, Any]] = []
    for item in entries:
        if isinstance(item, dict):
            resource = item.get("resource")
            if isinstance(resource, dict):
                result.append(resource)
    return result


def first_bundle_resource(payload: Any) -> dict[str, Any] | None:
    entries = bundle_entries(payload)
    return entries[0] if entries else None


def resource_id(reference: str | None, resource_type: str) -> str | None:
    if not reference:
        return None
    prefix = f"{resource_type}/"
    if reference.startswith(prefix):
        return reference[len(prefix):]
    return reference


def specialty_from_codeable_concepts(items: Iterable[dict[str, Any]]) -> tuple[int | None, str | None]:
    for item in items:
        for coding in item.get("coding", []):
            if coding.get("system") == SPECIALTY_SYSTEM and coding.get("code"):
                return int(coding["code"]), str(coding.get("display") or item.get("text") or "")
    return None, None


def document_identifier_system(tipo_documento: str) -> str:
    normalized = str(tipo_documento or "").strip().lower()
    return f"urn:medix:document:{normalized}"


def organization_to_legacy(resource: dict[str, Any]) -> dict[str, Any]:
    telecom = resource.get("telecom") or []
    address = resource.get("address") or []
    nit = None
    for identifier in resource.get("identifier", []):
        if identifier.get("system") == "urn:medix:nit":
            nit = identifier.get("value")
            break
    return {
        "id_ips": int(resource["id"]),
        "nombre": str(resource.get("name") or ""),
        "codigo": None,
        "nit": str(nit or ""),
        "direccion": str(address[0].get("text")) if address else None,
        "telefono": str(telecom[0].get("value")) if telecom else None,
        "estado": "ACTIVO" if bool(resource.get("active")) else "INACTIVO",
    }


def patient_to_legacy(resource: dict[str, Any]) -> dict[str, Any]:
    identifier = (resource.get("identifier") or [{}])[0]
    names = resource.get("name") or [{}]
    telecom = resource.get("telecom") or []
    phone = next((item.get("value") for item in telecom if item.get("system") == "phone"), None)
    email = next((item.get("value") for item in telecom if item.get("system") == "email"), None)
    identifier_system = str(identifier.get("system") or "")
    tipo_documento = str(((identifier.get("type") or {}).get("text")) or "")
    if not tipo_documento and identifier_system.startswith("urn:medix:document:"):
        tipo_documento = identifier_system.rsplit(":", 1)[-1].upper()
    return {
        "id_paciente": int(resource["id"]),
        "tipo_documento": tipo_documento,
        "numero_documento": str(identifier.get("value") or ""),
        "nombres": str((names[0].get("given") or [""])[0]),
        "apellidos": str(names[0].get("family") or ""),
        "fecha_nacimiento": resource.get("birthDate"),
        "telefono": phone,
        "correo": email,
        "estado": "ACTIVO" if bool(resource.get("active")) else "INACTIVO",
        "fecha_creacion": resource.get("meta", {}).get("lastUpdated") or "1970-01-01T00:00:00",
    }


def practitioner_role_to_legacy(resource: dict[str, Any]) -> dict[str, Any]:
    specialty_id, specialty_name = specialty_from_codeable_concepts(resource.get("specialty") or [])
    practitioner = resource.get("practitioner") or {}
    practitioner_id = resource_id(practitioner.get("reference"), "Practitioner")
    return {
        "id": int(practitioner_id or resource["id"]),
        "nombre_completo": str(practitioner.get("display") or ""),
        "id_especialidad": specialty_id,
        "nombre_especialidad": specialty_name,
    }


def slot_to_legacy(resource: dict[str, Any]) -> dict[str, Any]:
    slot_status = str(resource.get("status") or "")
    schedule = resource.get("schedule") or {}
    schedule_id = resource_id(schedule.get("reference"), "Schedule")
    return {
        "id_prestador": int(schedule_id or 0),
        "fecha_hora": resource.get("start"),
        "disponible": slot_status == "free",
        "bloqueado": slot_status == "busy-unavailable",
    }


def appointment_to_legacy(resource: dict[str, Any]) -> dict[str, Any]:
    patient_id = None
    practitioner_id = None
    for participant in resource.get("participant") or []:
        actor = participant.get("actor") or {}
        reference = actor.get("reference")
        if reference and reference.startswith("Patient/"):
            patient_id = int(resource_id(reference, "Patient"))
        if reference and reference.startswith("Practitioner/"):
            practitioner_id = int(resource_id(reference, "Practitioner"))

    specialty_id, _specialty_name = specialty_from_codeable_concepts(resource.get("specialty") or [])
    cancellation_reason = resource.get("cancelationReason") or {}
    created_at = resource.get("created") or "1970-01-01T00:00:00"
    updated_at = resource.get("meta", {}).get("lastUpdated") or created_at
    status = str(resource.get("status") or "")
    return {
        "id": int(resource["id"]),
        "id_paciente": int(patient_id or 0),
        "id_prestador": int(practitioner_id or 0),
        "id_especialidad": int(specialty_id or 0),
        "fecha_hora_cupo": resource.get("start"),
        "estado": "scheduled" if status == "booked" else "cancelled",
        "motivo_cancelacion": cancellation_reason.get("text"),
        "fecha_creacion": created_at,
        "fecha_actualizacion": updated_at,
    }


def build_appointment_resource(
    *,
    patient_id: int,
    provider_id: int,
    specialty_id: int,
    specialty_name: str | None,
    slot_start: datetime,
) -> dict[str, Any]:
    specialty = {
        "coding": [
            {
                "system": SPECIALTY_SYSTEM,
                "code": str(specialty_id),
                "display": specialty_name or str(specialty_id),
            }
        ],
        "text": specialty_name or str(specialty_id),
    }
    return {
        "resourceType": "Appointment",
        "status": "booked",
        "specialty": [specialty],
        "slot": [{"reference": f"Slot/{provider_id}-{slot_start.isoformat()}"}],
        "participant": [
            {"actor": {"reference": f"Patient/{patient_id}"}, "status": "accepted"},
            {"actor": {"reference": f"Practitioner/{provider_id}"}, "status": "accepted"},
        ],
    }


def build_cancel_patch(motivo: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "resourceType": "Appointment",
        "status": "cancelled",
    }
    if motivo:
        payload["cancelationReason"] = {"text": motivo}
    return payload


def build_reschedule_patch(
    *,
    provider_id: int,
    specialty_id: int,
    specialty_name: str | None,
    slot_start: datetime,
) -> dict[str, Any]:
    payload = build_appointment_resource(
        patient_id=0,
        provider_id=provider_id,
        specialty_id=specialty_id,
        specialty_name=specialty_name,
        slot_start=slot_start,
    )
    payload.pop("participant")
    return payload
