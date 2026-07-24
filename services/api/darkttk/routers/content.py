import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select

from ..content_history import record_content_event
from ..content_policy import moderate, normalize, record_moderation
from ..content_schemas import (
    BlockedTopicCreateRequest,
    BlockedTopicResponse,
    ContentHistoryResponse,
    FactCheckResponse,
    IdeaCreateRequest,
    IdeaGenerateRequest,
    IdeaResponse,
    NicheResponse,
    NicheUpdateRequest,
    ScriptGenerateRequest,
    ScriptResponse,
    ScriptRevisionRequest,
    SourceCreateRequest,
    SourceResponse,
)
from ..content_seed import ensure_content_defaults
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import (
    BlockedTopic,
    ContentEvent,
    ContentIdea,
    ContentNiche,
    FactCheck,
    RiskLevel,
    Role,
    Script,
    ScriptSource,
    Source,
)
from ..providers.ports import GeneratedIdea
from ..providers.registry import fact_checker, language_model

router = APIRouter(prefix="/v1/content", tags=["Content"])
CONTENT_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.EDITOR.value)
REVIEW_ROLES = CONTENT_ROLES + (Role.REVIEWER.value,)


def owned_niche(db: DbSession, organization_id: str, niche_id: str) -> ContentNiche:
    niche = db.scalar(
        select(ContentNiche).where(
            ContentNiche.id == niche_id,
            ContentNiche.organization_id == organization_id,
        )
    )
    if niche is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not niche.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "niche_disabled", "message": "Este nicho está desativado."},
        )
    return niche


def owned_idea(db: DbSession, organization_id: str, idea_id: str) -> ContentIdea:
    idea = db.scalar(
        select(ContentIdea).where(
            ContentIdea.id == idea_id,
            ContentIdea.organization_id == organization_id,
        )
    )
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return idea


def owned_script(db: DbSession, organization_id: str, script_id: str) -> Script:
    script = db.scalar(
        select(Script).where(
            Script.id == script_id,
            Script.organization_id == organization_id,
        )
    )
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return script


def idea_response(idea: ContentIdea) -> IdeaResponse:
    return IdeaResponse(
        **{
            column: getattr(idea, column)
            for column in (
                "id", "niche_id", "mode", "topic", "creative_angle", "content_promise",
                "hook", "narrative_structure", "key_information", "call_to_action",
                "visual_suggestion", "duration_seconds", "target_audience", "objective",
                "status", "risk_level", "provider_key", "created_at",
            )
        },
        provider_is_mock=(idea.provider_key or "").startswith("mock-"),
    )


def script_response(script: Script) -> ScriptResponse:
    return ScriptResponse(
        **{
            column: getattr(script, column)
            for column in (
                "id", "idea_id", "version", "style", "content", "status",
                "moderation_status", "fact_check_status", "provider_key", "created_at",
            )
        },
        provider_is_mock=(script.provider_key or "").startswith("mock-"),
    )


def ensure_allowed(decision, stage: str) -> None:
    if decision.result == "block":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "content_blocked",
                "message": f"Conteúdo bloqueado na etapa {stage}.",
                "rules": decision.matched_rules,
            },
        )


@router.get("/niches", response_model=list[NicheResponse])
def list_niches(context: CurrentAuth, db: DbSession):
    ensure_content_defaults(db, context.membership.organization_id)
    db.commit()
    return list(
        db.scalars(
            select(ContentNiche)
            .where(ContentNiche.organization_id == context.membership.organization_id)
            .order_by(ContentNiche.name)
        )
    )


@router.patch("/niches/{niche_id}", response_model=NicheResponse)
def update_niche(
    niche_id: str,
    payload: NicheUpdateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(Role.ADMIN.value, Role.MANAGER.value)),
):
    niche = db.scalar(
        select(ContentNiche).where(
            ContentNiche.id == niche_id,
            ContentNiche.organization_id == context.membership.organization_id,
        )
    )
    if niche is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    niche.enabled = payload.enabled
    db.commit()
    return niche


@router.get("/blocked-topics", response_model=list[BlockedTopicResponse])
def list_blocked_topics(context: CurrentAuth, db: DbSession):
    return list(
        db.scalars(
            select(BlockedTopic)
            .where(
                BlockedTopic.organization_id == context.membership.organization_id,
                BlockedTopic.active.is_(True),
            )
            .order_by(BlockedTopic.term)
        )
    )


@router.post(
    "/blocked-topics",
    response_model=BlockedTopicResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_blocked_topic(
    payload: BlockedTopicCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(Role.ADMIN.value, Role.MANAGER.value)),
):
    normalized = normalize(payload.term)
    duplicate = db.scalar(
        select(BlockedTopic).where(
            BlockedTopic.organization_id == context.membership.organization_id,
            BlockedTopic.normalized_term == normalized,
            BlockedTopic.kind == payload.kind.value,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "blocked_topic_exists", "message": "Bloqueio já cadastrado."},
        )
    item = BlockedTopic(
        organization_id=context.membership.organization_id,
        term=payload.term.strip(),
        normalized_term=normalized,
        kind=payload.kind.value,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="blocked_topic",
        subject_id=item.id,
        event_type="blocked_topic.created",
        payload={"term": item.term, "kind": item.kind},
    )
    db.commit()
    return item


@router.delete("/blocked-topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blocked_topic(
    topic_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(Role.ADMIN.value, Role.MANAGER.value)),
):
    item = db.scalar(
        select(BlockedTopic).where(
            BlockedTopic.id == topic_id,
            BlockedTopic.organization_id == context.membership.organization_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/ideas", response_model=list[IdeaResponse])
def list_ideas(context: CurrentAuth, db: DbSession, limit: int = 50):
    limit = min(max(limit, 1), 100)
    ideas = list(
        db.scalars(
            select(ContentIdea)
            .where(ContentIdea.organization_id == context.membership.organization_id)
            .order_by(ContentIdea.created_at.desc())
            .limit(limit)
        )
    )
    return [idea_response(idea) for idea in ideas]


@router.post("/ideas", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
def create_idea(
    payload: IdeaCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONTENT_ROLES)),
):
    owned_niche(db, context.membership.organization_id, payload.niche_id)
    decision = moderate(
        db,
        context.membership.organization_id,
        " ".join((payload.topic, payload.creative_angle, payload.hook, payload.key_information)),
    )
    ensure_allowed(decision, "pré-geração")
    idea = ContentIdea(
        organization_id=context.membership.organization_id,
        created_by=context.user.id,
        mode="manual",
        risk_level=RiskLevel.MEDIUM.value if decision.result == "review" else RiskLevel.LOW.value,
        **payload.model_dump(),
    )
    db.add(idea)
    db.flush()
    record_moderation(
        db,
        organization_id=context.membership.organization_id,
        subject_type="content_idea",
        subject_id=idea.id,
        stage="pre_generation",
        decision=decision,
    )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="content_idea",
        subject_id=idea.id,
        event_type="idea.created",
        payload={"mode": "manual", "risk_level": idea.risk_level},
    )
    db.commit()
    return idea_response(idea)


@router.post(
    "/ideas/generate",
    response_model=IdeaResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_idea(
    payload: IdeaGenerateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONTENT_ROLES)),
):
    niche = owned_niche(db, context.membership.organization_id, payload.niche_id)
    decision = moderate(
        db, context.membership.organization_id, f"{niche.name} {payload.topic} {payload.objective}"
    )
    ensure_allowed(decision, "pré-geração")
    provider = language_model()
    generated = provider.generate_idea(niche.name, payload.topic, payload.objective)
    idea = ContentIdea(
        organization_id=context.membership.organization_id,
        niche_id=niche.id,
        created_by=context.user.id,
        mode="ai_assisted",
        risk_level=RiskLevel.MEDIUM.value if decision.result == "review" else RiskLevel.LOW.value,
        provider_key=provider.provider_key,
        **generated.__dict__,
    )
    db.add(idea)
    db.flush()
    record_moderation(
        db,
        organization_id=context.membership.organization_id,
        subject_type="content_idea",
        subject_id=idea.id,
        stage="pre_generation",
        decision=decision,
    )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="content_idea",
        subject_id=idea.id,
        event_type="idea.generated",
        payload={"provider": provider.provider_key, "is_mock": provider.is_mock},
    )
    db.commit()
    return idea_response(idea)


@router.post(
    "/ideas/{idea_id}/scripts/generate",
    response_model=ScriptResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_script(
    idea_id: str,
    payload: ScriptGenerateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONTENT_ROLES)),
):
    idea = owned_idea(db, context.membership.organization_id, idea_id)
    provider = language_model()
    generated_idea = GeneratedIdea(
        topic=idea.topic,
        creative_angle=idea.creative_angle,
        content_promise=idea.content_promise,
        hook=idea.hook,
        narrative_structure=idea.narrative_structure,
        key_information=idea.key_information,
        call_to_action=idea.call_to_action,
        visual_suggestion=idea.visual_suggestion,
        duration_seconds=idea.duration_seconds,
        target_audience=idea.target_audience,
        objective=idea.objective,
    )
    generated = provider.generate_script(
        generated_idea, payload.style.value, payload.duration_seconds or idea.duration_seconds
    )
    version = (db.scalar(select(func.max(Script.version)).where(Script.idea_id == idea.id)) or 0) + 1
    script = Script(
        organization_id=context.membership.organization_id,
        idea_id=idea.id,
        created_by=context.user.id,
        version=version,
        style=generated.style,
        content=generated.content,
        provider_key=provider.provider_key,
    )
    db.add(script)
    db.flush()
    decision = moderate(db, context.membership.organization_id, script.content)
    record_moderation(
        db,
        organization_id=context.membership.organization_id,
        subject_type="script",
        subject_id=script.id,
        stage="pre_approval",
        decision=decision,
    )
    script.moderation_status = (
        "blocked" if decision.result == "block" else "needs_review"
        if decision.result == "review" else "verified"
    )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="script",
        subject_id=script.id,
        event_type="script.generated",
        payload={"version": version, "provider": provider.provider_key, "is_mock": provider.is_mock},
    )
    db.commit()
    return script_response(script)


@router.post(
    "/scripts/{script_id}/versions",
    response_model=ScriptResponse,
    status_code=status.HTTP_201_CREATED,
)
def revise_script(
    script_id: str,
    payload: ScriptRevisionRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONTENT_ROLES)),
):
    previous = owned_script(db, context.membership.organization_id, script_id)
    decision = moderate(db, context.membership.organization_id, payload.content)
    version = (db.scalar(select(func.max(Script.version)).where(Script.idea_id == previous.idea_id)) or 0) + 1
    script = Script(
        organization_id=context.membership.organization_id,
        idea_id=previous.idea_id,
        created_by=context.user.id,
        version=version,
        style=payload.style.value,
        content=payload.content,
        moderation_status="blocked" if decision.result == "block" else "needs_review"
        if decision.result == "review" else "verified",
        provider_key=None,
    )
    db.add(script)
    db.flush()
    record_moderation(
        db,
        organization_id=context.membership.organization_id,
        subject_type="script",
        subject_id=script.id,
        stage="pre_approval",
        decision=decision,
    )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="script",
        subject_id=script.id,
        event_type="script.revised",
        payload={"previous_script_id": previous.id, "version": version, "reason": payload.reason},
    )
    db.commit()
    return script_response(script)


@router.get("/ideas/{idea_id}/scripts", response_model=list[ScriptResponse])
def list_scripts(idea_id: str, context: CurrentAuth, db: DbSession):
    idea = owned_idea(db, context.membership.organization_id, idea_id)
    scripts = list(
        db.scalars(select(Script).where(Script.idea_id == idea.id).order_by(Script.version.desc()))
    )
    return [script_response(item) for item in scripts]


@router.post(
    "/scripts/{script_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_source(
    script_id: str,
    payload: SourceCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*REVIEW_ROLES)),
):
    script = owned_script(db, context.membership.organization_id, script_id)
    source = db.scalar(
        select(Source).where(
            Source.organization_id == context.membership.organization_id,
            Source.url == str(payload.url),
        )
    )
    if source is None:
        source = Source(
            organization_id=context.membership.organization_id,
            url=str(payload.url),
            title=payload.title,
            publisher=payload.publisher,
            trust_score=payload.trust_score,
            license_note=payload.license_note,
        )
        db.add(source)
        db.flush()
    association = db.scalar(
        select(ScriptSource).where(
            ScriptSource.script_id == script.id,
            ScriptSource.source_id == source.id,
        )
    )
    if association is None:
        db.add(
            ScriptSource(
                organization_id=context.membership.organization_id,
                script_id=script.id,
                source_id=source.id,
                created_by=context.user.id,
            )
        )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="script",
        subject_id=script.id,
        event_type="source.attached",
        payload={"source_id": source.id, "trust_score": source.trust_score},
    )
    db.commit()
    return source


@router.post("/scripts/{script_id}/fact-checks/run", response_model=list[FactCheckResponse])
def run_fact_check(
    script_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*REVIEW_ROLES)),
):
    script = owned_script(db, context.membership.organization_id, script_id)
    attached_sources = list(
        db.scalars(select(ScriptSource).where(ScriptSource.script_id == script.id))
    )
    source_count = len(attached_sources)
    provider = fact_checker()
    checked = provider.check(script.content, source_count)
    db.query(FactCheck).filter(FactCheck.script_id == script.id).delete()
    rows: list[FactCheck] = []
    for item in checked:
        row = FactCheck(
            organization_id=context.membership.organization_id,
            script_id=script.id,
            source_id=attached_sources[0].source_id if attached_sources else None,
            claim=item.claim,
            verdict=item.verdict,
            confidence=item.confidence,
            evidence=item.evidence,
            provider_key=provider.provider_key,
        )
        db.add(row)
        rows.append(row)
    script.fact_check_status = (
        "verified" if rows and all(row.verdict == "supported" for row in rows)
        else "needs_review" if rows else "verified"
    )
    record_content_event(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        subject_type="script",
        subject_id=script.id,
        event_type="fact_check.completed",
        payload={"claims": len(rows), "provider": provider.provider_key, "is_mock": provider.is_mock},
    )
    db.commit()
    return [
        FactCheckResponse(
            id=row.id,
            claim=row.claim,
            verdict=row.verdict,
            confidence=row.confidence,
            evidence=row.evidence,
            provider_key=row.provider_key,
            provider_is_mock=provider.is_mock,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/history/{subject_type}/{subject_id}", response_model=list[ContentHistoryResponse])
def content_history(subject_type: str, subject_id: str, context: CurrentAuth, db: DbSession):
    events = list(
        db.scalars(
            select(ContentEvent)
            .where(
                ContentEvent.organization_id == context.membership.organization_id,
                ContentEvent.subject_type == subject_type,
                ContentEvent.subject_id == subject_id,
            )
            .order_by(ContentEvent.created_at)
        )
    )
    return [
        ContentHistoryResponse(
            id=item.id,
            event_type=item.event_type,
            subject_type=item.subject_type,
            subject_id=item.subject_id,
            actor_id=item.actor_id,
            payload=json.loads(item.payload_json),
            created_at=item.created_at,
        )
        for item in events
    ]
