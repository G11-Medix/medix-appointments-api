import httpx
import pytest
from fastapi import HTTPException

from app.clients.ips_client import IpsClient


def test_timeout_maps_to_504(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(**kwargs):  # noqa: ANN003
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "request", raise_timeout)
    client = IpsClient(timeout_seconds=0.1)

    with pytest.raises(HTTPException) as exc:
        client.request(
            method="GET",
            base_url="http://localhost:4011",
            path="/fhir/Appointment",
        )

    assert exc.value.status_code == 504


def test_connection_error_maps_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "http://localhost:4011/fhir/Appointment")

    def raise_connect_error(**kwargs):  # noqa: ANN003
        raise httpx.ConnectError("connect", request=request)

    monkeypatch.setattr(httpx, "request", raise_connect_error)
    client = IpsClient(timeout_seconds=0.1)

    with pytest.raises(HTTPException) as exc:
        client.request(
            method="GET",
            base_url="http://localhost:4011",
            path="/fhir/Appointment",
        )

    assert exc.value.status_code == 502


def test_upstream_error_propagates_status_and_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    def return_conflict(**kwargs):  # noqa: ANN003
        request = httpx.Request("PATCH", "http://localhost:4011/fhir/Appointment/1")
        return httpx.Response(status_code=409, json={"detail": "Solo las citas programadas pueden reprogramarse"}, request=request)

    monkeypatch.setattr(httpx, "request", return_conflict)
    client = IpsClient(timeout_seconds=0.1)

    with pytest.raises(HTTPException) as exc:
        client.request(
            method="PATCH",
            base_url="http://localhost:4011",
            path="/fhir/Appointment/1",
            payload={"slot": [{"reference": "Slot/7-2026-04-01T08:00:00"}]},
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Solo las citas programadas pueden reprogramarse"


def test_operation_outcome_error_maps_to_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    def return_operation_outcome(**kwargs):  # noqa: ANN003
        request = httpx.Request("GET", "http://localhost:4011/fhir/Patient/999")
        return httpx.Response(
            status_code=404,
            json={
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "not-found", "diagnostics": "Patient no encontrado"}],
            },
            request=request,
        )

    monkeypatch.setattr(httpx, "request", return_operation_outcome)
    client = IpsClient(timeout_seconds=0.1)

    with pytest.raises(HTTPException) as exc:
        client.request(
            method="GET",
            base_url="http://localhost:4011",
            path="/fhir/Patient/999",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Patient no encontrado"
