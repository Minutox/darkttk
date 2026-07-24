from sqlalchemy import select

from .content_seed import ensure_content_defaults
from .database import Base, SessionLocal, engine
from .models import Organization, OrganizationMember, Role, SystemSetting, User
from .security import hash_password


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "admin@darkttk.local")):
            return
        organization = Organization(name="DarkTTK Studio", slug="darkttk-studio")
        admin = User(
            email="admin@darkttk.local",
            display_name="Administrador",
            password_hash=hash_password("DarkTTK#Local2026"),
        )
        db.add_all([organization, admin])
        db.flush()
        db.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=admin.id,
                role=Role.ADMIN.value,
            )
        )
        db.add_all(
            [
                SystemSetting(
                    organization_id=organization.id,
                    key="publishing.daily_limit",
                    value_json="5",
                ),
                SystemSetting(
                    organization_id=organization.id,
                    key="publishing.requires_approval",
                    value_json="true",
                ),
                SystemSetting(
                    organization_id=organization.id,
                    key="timezone",
                    value_json='"America/Sao_Paulo"',
                ),
            ]
        )
        ensure_content_defaults(db, organization.id)
        db.commit()


if __name__ == "__main__":
    seed()
