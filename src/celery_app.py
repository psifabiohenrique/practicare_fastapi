from celery import Celery

from settings import settings


celery_app = Celery(
    "practicare",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# celery_app.autodiscover_tasks(["src.tasks"])
celery_app.conf.imports = ("tasks.record_generation",)
