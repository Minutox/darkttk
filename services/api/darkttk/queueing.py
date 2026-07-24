from celery import Celery

from .config import get_settings

settings = get_settings()
celery_app = Celery(
    "darkttk",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "darkttk.render.execute": {"queue": "video.render"},
        "darkttk.publish.execute": {"queue": "social.publish"},
        "darkttk.publish.poll": {"queue": "social.publish"},
        "darkttk.analytics.sync": {"queue": "social.metrics"},
    },
    task_time_limit=settings.render_timeout_seconds + 60,
    task_annotations={
        "darkttk.publish.execute": {
            "time_limit": settings.publishing_timeout_seconds,
            "soft_time_limit": settings.publishing_timeout_seconds - 30,
        },
        "darkttk.publish.poll": {"time_limit": 60},
    },
)


def enqueue_render(job_id: str) -> str:
    result = celery_app.send_task("darkttk.render.execute", args=[job_id])
    return str(result.id)


def enqueue_publication(job_id: str, eta=None) -> str:
    result = celery_app.send_task("darkttk.publish.execute", args=[job_id], eta=eta)
    return str(result.id)


def enqueue_metric_sync(job_id: str) -> str:
    result = celery_app.send_task("darkttk.analytics.sync", args=[job_id])
    return str(result.id)
