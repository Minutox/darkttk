import json
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from ..analytics_schemas import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentStatusRequest,
    ExperimentVariantResponse,
    MetricSnapshotResponse,
    OverviewResponse,
    RecommendationDecisionRequest,
    RecommendationResponse,
    RetentionImportRequest,
    RetentionResponse,
)
from ..analytics_worker import sync_publication_metrics
from ..audit import write_audit
from ..dependencies import AuthContext, DbSession, require_roles
from ..models import (
    AccountMetricSnapshot,
    AnalyticsRecommendation,
    ContentExperiment,
    ExperimentStatus,
    ExperimentVariant,
    PublicationJob,
    PublicationMetricSnapshot,
    RetentionObservation,
    Role,
    VideoProject,
    utcnow,
)
from ..queueing import enqueue_metric_sync

router = APIRouter(prefix="/v1/analytics", tags=["Analytics"])
READ_ROLES = (
    Role.ADMIN.value,
    Role.MANAGER.value,
    Role.ANALYST.value,
    Role.VIEWER.value,
)
MANAGE_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.ANALYST.value)


def latest_publication_metrics(db: DbSession, organization_id: str):
    snapshots = list(
        db.scalars(
            select(PublicationMetricSnapshot)
            .where(PublicationMetricSnapshot.organization_id == organization_id)
            .order_by(PublicationMetricSnapshot.collected_at.desc())
        )
    )
    latest: dict[str, PublicationMetricSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.publication_job_id, snapshot)
    return list(latest.values())


def retention_response(observation: RetentionObservation) -> RetentionResponse:
    return RetentionResponse(
        id=observation.id,
        publication_job_id=observation.publication_job_id,
        source=observation.source,
        average_watch_time_seconds=observation.average_watch_time_seconds,
        completion_rate=observation.completion_rate,
        watched_full_rate=observation.watched_full_rate,
        saved_count=observation.saved_count,
        retention_curve=json.loads(observation.curve_json),
        collected_at=observation.collected_at,
    )


def overview_for(db: DbSession, organization_id: str) -> OverviewResponse:
    metrics = latest_publication_metrics(db, organization_id)
    views = sum(item.view_count for item in metrics)
    likes = sum(item.like_count for item in metrics)
    comments = sum(item.comment_count for item in metrics)
    shares = sum(item.share_count for item in metrics)
    account_snapshots = list(
        db.scalars(
            select(AccountMetricSnapshot)
            .where(AccountMetricSnapshot.organization_id == organization_id)
            .order_by(AccountMetricSnapshot.collected_at.desc())
            .limit(2)
        )
    )
    retention = list(
        db.scalars(
            select(RetentionObservation)
            .where(RetentionObservation.organization_id == organization_id)
            .order_by(RetentionObservation.collected_at.desc())
        )
    )
    latest_retention: dict[str, RetentionObservation] = {}
    for item in retention:
        latest_retention.setdefault(item.publication_job_id, item)
    completion_values = [
        item.completion_rate
        for item in latest_retention.values()
        if item.completion_rate is not None
    ]
    is_mock = bool(metrics) and all(item.is_mock for item in metrics)
    return OverviewResponse(
        videos_with_data=len(metrics),
        total_views=views,
        total_likes=likes,
        total_comments=comments,
        total_shares=shares,
        engagement_rate=(likes + comments + shares) / views if views else 0,
        follower_count=account_snapshots[0].follower_count if account_snapshots else None,
        follower_delta=(
            account_snapshots[0].follower_count - account_snapshots[1].follower_count
            if len(account_snapshots) > 1
            else None
        ),
        average_completion_rate=(
            sum(completion_values) / len(completion_values)
            if completion_values
            else None
        ),
        source_notice=(
            "Dados simulados; não representam desempenho real."
            if is_mock
            else "Contagens públicas vêm da TikTok Display API; retenção depende de importação identificada."
        ),
        is_mock=is_mock,
    )


@router.get("/overview", response_model=OverviewResponse)
def analytics_overview(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*READ_ROLES)),
):
    return overview_for(db, context.membership.organization_id)


@router.post(
    "/publications/{job_id}/sync",
    response_model=MetricSnapshotResponse | dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def sync_metrics(
    job_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    job = db.scalar(
        select(PublicationJob).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    if job.is_mock:
        outcome = sync_publication_metrics(job.id)
        if outcome != "synced":
            raise HTTPException(status_code=409, detail={"code": outcome})
        db.expire_all()
        snapshot = db.scalar(
            select(PublicationMetricSnapshot)
            .where(PublicationMetricSnapshot.publication_job_id == job.id)
            .order_by(PublicationMetricSnapshot.collected_at.desc())
        )
        return MetricSnapshotResponse.model_validate(snapshot)
    try:
        task_id = enqueue_metric_sync(job.id)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "analytics_queue_unavailable", "message": str(error)[:300]},
        ) from error
    return {"queued": True, "task_id": task_id}


@router.get("/publications/{job_id}/metrics", response_model=list[MetricSnapshotResponse])
def publication_metrics(
    job_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*READ_ROLES)),
):
    job = db.scalar(
        select(PublicationJob.id).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    return list(
        db.scalars(
            select(PublicationMetricSnapshot)
            .where(PublicationMetricSnapshot.publication_job_id == job_id)
            .order_by(PublicationMetricSnapshot.collected_at.desc())
        )
    )


@router.post(
    "/publications/{job_id}/retention",
    response_model=RetentionResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_retention(
    job_id: str,
    payload: RetentionImportRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    job = db.scalar(
        select(PublicationJob).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    observation = RetentionObservation(
        organization_id=context.membership.organization_id,
        publication_job_id=job.id,
        imported_by=context.user.id,
        source=payload.source,
        average_watch_time_seconds=payload.average_watch_time_seconds,
        completion_rate=payload.completion_rate,
        watched_full_rate=payload.watched_full_rate,
        saved_count=payload.saved_count,
        curve_json=json.dumps(payload.retention_curve, separators=(",", ":")),
        collected_at=payload.collected_at,
    )
    db.add(observation)
    db.flush()
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="analytics.retention_imported",
        entity_type="publication_job",
        entity_id=job.id,
        metadata={"source": payload.source},
    )
    db.commit()
    return retention_response(observation)


@router.post("/recommendations/generate", response_model=list[RecommendationResponse])
def generate_recommendations(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    organization_id = context.membership.organization_id
    overview = overview_for(db, organization_id)
    candidates: list[tuple[str, str, str, int, dict[str, object]]] = []
    evidence = overview.model_dump()
    if overview.videos_with_data < 2:
        candidates.append(
            (
                "data_quality",
                "Colete mais publicações antes de alterar a estratégia",
                "A amostra atual é pequena; decisões automáticas teriam baixa confiabilidade.",
                95,
                evidence,
            )
        )
    elif overview.engagement_rate < 0.05:
        candidates.append(
            (
                "hook",
                "Teste um gancho mais direto",
                "A taxa combinada de interação está abaixo de 5%. Compare duas aberturas sem duplicar o restante do vídeo.",
                72,
                evidence,
            )
        )
    else:
        share_rate = overview.total_shares / overview.total_views if overview.total_views else 0
        if share_rate >= 0.01:
            candidates.append(
                (
                    "series",
                    "Transforme o formato mais compartilhado em série",
                    "A proporção de compartilhamentos indica utilidade recorrente. Preserve o tema e varie a entrega.",
                    81,
                    evidence,
                )
            )
    if overview.average_completion_rate is not None and overview.average_completion_rate < 0.4:
        candidates.append(
            (
                "retention",
                "Encurte a promessa e antecipe a entrega",
                "A conclusão média importada ficou abaixo de 40%. Teste uma versão mais curta com o mesmo valor editorial.",
                78,
                evidence,
            )
        )
    created = []
    for kind, title, rationale, confidence, candidate_evidence in candidates:
        fingerprint = sha256(
            f"{kind}:{overview.videos_with_data}:{overview.total_views}:{overview.average_completion_rate}".encode()
        ).hexdigest()
        existing = db.scalar(
            select(AnalyticsRecommendation).where(
                AnalyticsRecommendation.organization_id == organization_id,
                AnalyticsRecommendation.evidence_hash == fingerprint,
            )
        )
        if existing:
            created.append(existing)
            continue
        recommendation = AnalyticsRecommendation(
            organization_id=organization_id,
            kind=kind,
            title=title,
            rationale=rationale,
            confidence=confidence,
            evidence_hash=fingerprint,
            evidence_json=json.dumps(candidate_evidence, separators=(",", ":")),
        )
        db.add(recommendation)
        created.append(recommendation)
    db.commit()
    return created


@router.get("/recommendations", response_model=list[RecommendationResponse])
def list_recommendations(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*READ_ROLES)),
):
    return list(
        db.scalars(
            select(AnalyticsRecommendation)
            .where(
                AnalyticsRecommendation.organization_id
                == context.membership.organization_id
            )
            .order_by(AnalyticsRecommendation.created_at.desc())
        )
    )


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def decide_recommendation(
    recommendation_id: str,
    payload: RecommendationDecisionRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    recommendation = db.scalar(
        select(AnalyticsRecommendation).where(
            AnalyticsRecommendation.id == recommendation_id,
            AnalyticsRecommendation.organization_id
            == context.membership.organization_id,
        )
    )
    if recommendation is None:
        raise HTTPException(status_code=404)
    recommendation.status = payload.decision.value
    recommendation.decided_by = context.user.id
    recommendation.decided_at = utcnow()
    db.commit()
    return recommendation


def variant_metric(db: DbSession, variant: ExperimentVariant, metric: str) -> tuple[int, float | None]:
    jobs = list(
        db.scalars(
            select(PublicationJob).where(
                PublicationJob.video_project_id == variant.video_project_id,
                PublicationJob.organization_id == variant.organization_id,
            )
        )
    )
    latest = []
    for job in jobs:
        snapshot = db.scalar(
            select(PublicationMetricSnapshot)
            .where(PublicationMetricSnapshot.publication_job_id == job.id)
            .order_by(PublicationMetricSnapshot.collected_at.desc())
        )
        if snapshot:
            latest.append(snapshot)
    views = sum(item.view_count for item in latest)
    if metric == "views":
        return views, float(views)
    if metric == "completion_rate":
        observations = []
        for job in jobs:
            item = db.scalar(
                select(RetentionObservation)
                .where(RetentionObservation.publication_job_id == job.id)
                .order_by(RetentionObservation.collected_at.desc())
            )
            if item and item.completion_rate is not None:
                observations.append(item.completion_rate)
        return views, sum(observations) / len(observations) if observations else None
    if not views:
        return 0, None
    if metric == "share_rate":
        return views, sum(item.share_count for item in latest) / views
    interactions = sum(
        item.like_count + item.comment_count + item.share_count for item in latest
    )
    return views, interactions / views


def experiment_response(db: DbSession, experiment: ContentExperiment) -> ExperimentResponse:
    variants = list(
        db.scalars(
            select(ExperimentVariant)
            .where(ExperimentVariant.experiment_id == experiment.id)
            .order_by(ExperimentVariant.label)
        )
    )
    responses = []
    for variant in variants:
        views, value = variant_metric(db, variant, experiment.primary_metric)
        responses.append(
            ExperimentVariantResponse(
                id=variant.id,
                label=variant.label,
                video_project_id=variant.video_project_id,
                variable_value=variant.variable_value,
                views=views,
                metric_value=value,
            )
        )
    eligible = [item for item in responses if item.metric_value is not None]
    winner = max(eligible, key=lambda item: item.metric_value).label if len(eligible) == 2 else None
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        hypothesis=experiment.hypothesis,
        variable=experiment.variable,
        primary_metric=experiment.primary_metric,
        status=experiment.status,
        created_at=experiment.created_at,
        variants=responses,
        winner_label=winner,
    )


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
def create_experiment(
    payload: ExperimentCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    organization_id = context.membership.organization_id
    projects = list(
        db.scalars(
            select(VideoProject).where(
                VideoProject.organization_id == organization_id,
                VideoProject.id.in_([item.video_project_id for item in payload.variants]),
            )
        )
    )
    if len(projects) != 2:
        raise HTTPException(status_code=422, detail={"code": "experiment_projects_invalid"})
    experiment = ContentExperiment(
        organization_id=organization_id,
        created_by=context.user.id,
        name=payload.name,
        hypothesis=payload.hypothesis,
        variable=payload.variable.value,
        primary_metric=payload.primary_metric.value,
    )
    db.add(experiment)
    db.flush()
    for variant in payload.variants:
        db.add(
            ExperimentVariant(
                organization_id=organization_id,
                experiment_id=experiment.id,
                video_project_id=variant.video_project_id,
                label=variant.label,
                variable_value=variant.variable_value,
            )
        )
    db.commit()
    return experiment_response(db, experiment)


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*READ_ROLES)),
):
    experiments = db.scalars(
        select(ContentExperiment)
        .where(
            ContentExperiment.organization_id == context.membership.organization_id
        )
        .order_by(ContentExperiment.created_at.desc())
    )
    return [experiment_response(db, item) for item in experiments]


@router.patch("/experiments/{experiment_id}", response_model=ExperimentResponse)
def update_experiment(
    experiment_id: str,
    payload: ExperimentStatusRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    experiment = db.scalar(
        select(ContentExperiment).where(
            ContentExperiment.id == experiment_id,
            ContentExperiment.organization_id == context.membership.organization_id,
        )
    )
    if experiment is None:
        raise HTTPException(status_code=404)
    transitions = {
        ExperimentStatus.DRAFT.value: {"running", "cancelled"},
        ExperimentStatus.RUNNING.value: {"completed", "cancelled"},
    }
    if payload.status not in transitions.get(experiment.status, set()):
        raise HTTPException(status_code=409, detail={"code": "invalid_experiment_transition"})
    experiment.status = payload.status
    if payload.status == "running":
        experiment.started_at = utcnow()
    if payload.status in {"completed", "cancelled"}:
        experiment.completed_at = utcnow()
    db.commit()
    return experiment_response(db, experiment)
