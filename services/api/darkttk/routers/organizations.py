from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from ..audit import write_audit
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import OrganizationMember, Role, User, UserStatus
from ..schemas import InviteMemberRequest, MemberResponse, UpdateMemberRoleRequest

router = APIRouter(prefix="/v1/organizations", tags=["Organizations"])

MANAGE_ROLES = (Role.ADMIN.value, Role.MANAGER.value)
ROLE_PERMISSIONS = {
    Role.ADMIN.value: ["*"],
    Role.MANAGER.value: [
        "content.manage", "approval.manage", "schedule.manage", "analytics.read", "members.read"
    ],
    Role.EDITOR.value: ["content.create", "content.edit", "library.manage"],
    Role.REVIEWER.value: ["content.read", "approval.decide", "sources.read"],
    Role.ANALYST.value: ["content.read", "analytics.read", "experiments.manage"],
    Role.VIEWER.value: ["content.read", "analytics.read"],
}


def member_response(member: OrganizationMember, user: User) -> MemberResponse:
    return MemberResponse(
        id=member.id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=member.role,
        status=user.status,
        created_at=member.created_at,
    )


@router.get("/current/members", response_model=list[MemberResponse])
def list_members(context: CurrentAuth, db: DbSession):
    rows = db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == context.membership.organization_id)
        .order_by(User.display_name)
    ).all()
    return [member_response(member, user) for member, user in rows]


@router.get("/current/permissions")
def current_permissions(context: CurrentAuth):
    return {
        "role": context.membership.role,
        "permissions": ROLE_PERMISSIONS[context.membership.role],
    }


@router.post(
    "/current/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    payload: InviteMemberRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    if context.membership.role == Role.MANAGER.value and payload.role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "permission_denied", "message": "Gestores não podem convidar administradores."},
        )
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=None,
            status=UserStatus.INVITED.value,
        )
        db.add(user)
        db.flush()
    existing = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == context.membership.organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "member_exists", "message": "Este usuário já pertence à organização."},
        )
    member = OrganizationMember(
        organization_id=context.membership.organization_id,
        user_id=user.id,
        role=payload.role.value,
    )
    db.add(member)
    db.flush()
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="member.invited",
        entity_type="organization_member",
        entity_id=member.id,
        metadata={"role": member.role, "email": email},
    )
    db.commit()
    return member_response(member, user)


@router.patch("/current/members/{member_id}", response_model=MemberResponse)
def update_member_role(
    member_id: str,
    payload: UpdateMemberRoleRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*MANAGE_ROLES)),
):
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == context.membership.organization_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if context.membership.role == Role.MANAGER.value and (
        member.role == Role.ADMIN.value or payload.role == Role.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "permission_denied", "message": "Apenas administradores gerenciam administradores."},
        )
    if member.role == Role.ADMIN.value and payload.role != Role.ADMIN:
        admin_count = db.scalar(
            select(func.count()).select_from(OrganizationMember).where(
                OrganizationMember.organization_id == context.membership.organization_id,
                OrganizationMember.role == Role.ADMIN.value,
            )
        )
        if admin_count == 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "last_admin", "message": "A organização precisa manter um administrador."},
            )
    previous_role = member.role
    member.role = payload.role.value
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="member.role_changed",
        entity_type="organization_member",
        entity_id=member.id,
        metadata={"previous_role": previous_role, "role": member.role},
    )
    db.commit()
    user = db.get(User, member.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return member_response(member, user)
