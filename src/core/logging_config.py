import json
import logging
import logging.config
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from src.settings import settings

# ContextVar para armazenar o correlation_id de forma segura
correlation_id_ctx: ContextVar[str] = ContextVar(
    "correlation_id", default="no-id"
)


class JSONFormatter(logging.Formatter):
    """
    Formatador customizado que transforma LogRecord em uma string JSON.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: PLR6301
        # Campos básicos
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "no-id"),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
        }

        # Incluir detalhes de exceção se existirem
        if record.exc_info:
            log_data["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        # Incluir campos extras passados no log (ex: extra={"user_id": 1})
        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "correlation_id",
        }
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                log_data[key] = value

        return json.dumps(log_data)


class CorrelationIdFilter(logging.Filter):
    """
    Filtro que injeta o correlation_id atual no LogRecord.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: PLR6301
        record.correlation_id = correlation_id_ctx.get()
        return True


def setup_logging():
    """
    Configura o sistema de logging global.
    """
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter,
            },
        },
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "simple": {
                "format": "%(levelname)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
                "filters": ["correlation_id"],
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "app.log",
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "formatter": "json",
                "filters": ["correlation_id"],
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "error.log",
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "formatter": "json",
                "level": "ERROR",
                "filters": ["correlation_id"],
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console", "app_file", "error_file"],
        },
    }

    logging.config.dictConfig(config)
