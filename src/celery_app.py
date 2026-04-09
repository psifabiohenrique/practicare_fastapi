from celery import Celery
from celery.signals import before_task_publish, task_prerun, worker_init

from src.core.logging_config import correlation_id_ctx, setup_logging
from src.settings import settings


@worker_init.connect
def setup_celery_logging(*args, **kwargs):  # pragma: no cover
    setup_logging()


@before_task_publish.connect
def inject_correlation_id(headers, **kwargs):
    # Pega o ID atual do contexto do FastAPI e injeta nos headers da task
    headers["correlation_id"] = correlation_id_ctx.get()


@task_prerun.connect
def extract_correlation_id(task, **kwargs):  # pragma: no cover
    # Recupera o ID dos headers da task recebida e ativa no contexto do Worker
    correlation_id = task.request.get("correlation_id", "no-id")
    correlation_id_ctx.set(correlation_id)


celery_app = Celery(
    "practicare",
    broker=settings.REDIS_URL,
)

# celery_app.autodiscover_tasks(["src.tasks"])
celery_app.conf.imports = (
    "src.tasks.record_generation",
    "src.tasks.report_generation",
    "src.tasks.context_update",
    "src.tasks.context_generation",
)


# Used to serialize audiobytes need to be removed when
#  audio files become stored
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
