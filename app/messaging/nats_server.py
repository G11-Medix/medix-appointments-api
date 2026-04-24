import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.messaging.nats_contracts import NatsCommandEnvelope, NatsErrorPayload, NatsResponseEnvelope
from app.messaging.nats_handlers import NatsApiHandlers

LOGGER = logging.getLogger(__name__)

HandlerFn = Callable[[dict[str, Any], str], Any]


class NatsRequestReplyServer:
    def __init__(
        self,
        *,
        handlers: NatsApiHandlers,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.handlers = handlers
        self.settings = settings or get_settings()
        self.logger = logger or LOGGER
        self._nc: Any | None = None
        self._subscriptions: list[Any] = []
        self._handler_map: dict[str, HandlerFn] = {
            "especialidades.listar": handlers.handle_list_especialidades,
            "instituciones.listar": handlers.handle_list_instituciones,
            "assistant.buscar_paciente": handlers.handle_assistant_find_patient,
            "assistant.instituciones_por_especialidad": handlers.handle_assistant_list_instituciones,
            "assistant.disponibilidad": handlers.handle_assistant_get_disponibilidad,
            "pacientes.buscar": handlers.handle_assistant_find_patient,
            "pacientes.obtener": handlers.handle_get_paciente,
            "citas.crear": handlers.handle_cita_create,
            "citas.obtener": handlers.handle_cita_get,
            "citas.listar": handlers.handle_cita_list,
            "citas.confirmacion": handlers.handle_cita_confirmacion,
            "citas.cancelar": handlers.handle_cita_cancelar,
            "citas.reprogramar": handlers.handle_cita_reprogramar,
            "citas.listar_por_paciente": handlers.handle_cita_listar_por_paciente,
            "pacientes.citas.listar": handlers.handle_cita_listar_por_paciente,
            "instituciones.disponibilidad": handlers.handle_assistant_get_disponibilidad,
        }

    async def start(self) -> None:
        if not self.settings.nats_enabled:
            return
        try:
            self._nc = await self._connect()
        except Exception:
            self.logger.exception("No fue posible conectar con NATS")
            return

        for suffix in self._handler_map:
            subject = self.build_subject(suffix)
            subscription = await self._nc.subscribe(
                subject,
                queue=self.settings.nats_queue_group,
                cb=self._build_callback(suffix),
            )
            self._subscriptions.append(subscription)
            self.logger.info("Suscrito a NATS subject %s", subject)

    async def close(self) -> None:
        if self._nc is None:
            return
        try:
            await self._nc.drain()
        except Exception:
            self.logger.exception("No fue posible cerrar NATS limpiamente")
        finally:
            self._nc = None
            self._subscriptions = []

    def build_subject(self, suffix: str) -> str:
        prefix = self.settings.nats_subject_prefix.strip(".")
        suffix = suffix.strip(".")
        return f"{prefix}.{suffix}" if prefix else suffix

    async def handle_message(self, operation: str, data: bytes) -> NatsResponseEnvelope:
        try:
            envelope = NatsCommandEnvelope.model_validate_json(data)
            normalized_operation = envelope.operation or operation
            if normalized_operation != operation:
                raise HTTPException(status_code=400, detail="Operacion no coincide con subject")
            handler = self._handler_map.get(operation)
            if handler is None:
                raise HTTPException(status_code=404, detail="Operacion NATS no soportada")
            self.handlers.authenticate(envelope.access_token)
            result = handler(envelope.payload, envelope.access_token)
            return NatsResponseEnvelope(
                correlation_id=envelope.correlation_id,
                success=True,
                data=result,
            )
        except HTTPException as exc:
            return self._error_response(
                correlation_id=self._extract_correlation_id(data),
                code=exc.status_code,
                detail=str(exc.detail),
            )
        except Exception as exc:
            self.logger.exception("Error procesando mensaje NATS para %s", operation)
            return self._error_response(
                correlation_id=self._extract_correlation_id(data),
                code=500,
                detail=str(exc),
            )

    def _build_callback(self, operation: str) -> Callable[[Any], Awaitable[None]]:
        async def _callback(msg: Any) -> None:
            response = await self.handle_message(operation, msg.data)
            if getattr(msg, "reply", None):
                await msg.respond(response.model_dump_json().encode("utf-8"))

        return _callback

    async def _connect(self) -> Any:
        import nats

        return await nats.connect(
            self.settings.nats_url,
            connect_timeout=self.settings.nats_connect_timeout_seconds,
        )

    @staticmethod
    def _error_response(*, correlation_id: str, code: int, detail: str) -> NatsResponseEnvelope:
        return NatsResponseEnvelope(
            correlation_id=correlation_id,
            success=False,
            data=None,
            error=NatsErrorPayload(code=code, detail=detail),
        )

    @staticmethod
    def _extract_correlation_id(data: bytes) -> str:
        try:
            envelope = NatsCommandEnvelope.model_validate_json(data)
            return envelope.correlation_id
        except Exception:
            return "unknown"
