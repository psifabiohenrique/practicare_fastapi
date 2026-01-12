import time

from celery_app import celery_app


@celery_app.task(bind=True)
def generate_record_task(self, value: int):
    print(f"[CELERY] Task started with value={value}")
    time.sleep(5)
    print("[CELERY] Task finished")
    return value * 2
