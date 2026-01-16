from celery import Celery

from src.settings import settings

celery_app = Celery(
    "practicare",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# celery_app.autodiscover_tasks(["src.tasks"])
celery_app.conf.imports = ("src.tasks.record_generation",)


# Used to serialize audiobytes need to be removed when
#  audio files become stored
celery_app.conf.update(
    task_serializer="pickle",
    accept_content=["pickle"],
    result_serializer="pickle",
)
