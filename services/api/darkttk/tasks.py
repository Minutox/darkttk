from .queueing import celery_app
from .analytics_worker import sync_publication_metrics
from .render_worker import execute_render_job
from .publishing_worker import (
    execute_publication_job,
    mark_publication_poll_timeout,
    poll_publication_job,
)


@celery_app.task(
    bind=True,
    name="darkttk.render.execute",
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def render_video(self, job_id: str) -> None:
    execute_render_job(job_id)


@celery_app.task(bind=True, name="darkttk.publish.execute", max_retries=5)
def publish_video(self, job_id: str) -> None:
    outcome = execute_publication_job(job_id)
    if outcome == "retry":
        raise self.retry(countdown=min(900, 30 * (2 ** self.request.retries)))
    if outcome == "poll":
        celery_app.send_task("darkttk.publish.poll", args=[job_id], countdown=20)


@celery_app.task(bind=True, name="darkttk.publish.poll", max_retries=30)
def poll_publication(self, job_id: str) -> None:
    should_continue = poll_publication_job(job_id)
    if should_continue:
        if self.request.retries >= self.max_retries - 1:
            mark_publication_poll_timeout(job_id)
            return
        raise self.retry(countdown=min(300, 20 + self.request.retries * 10))


@celery_app.task(
    bind=True,
    name="darkttk.analytics.sync",
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def sync_metrics(self, job_id: str) -> None:
    sync_publication_metrics(job_id)
