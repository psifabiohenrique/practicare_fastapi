import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging_config import correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: PLR6301
        # Tenta pegar um ID já existente ou gera um novo UUID
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )

        # Seta o ID no contexto para ser usado por loggers
        token = correlation_id_ctx.set(correlation_id)

        try:
            response = await call_next(request)
            # Adiciona o ID no header da resposta
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Limpa o contexto após a requisição finalizar
            correlation_id_ctx.reset(token)
