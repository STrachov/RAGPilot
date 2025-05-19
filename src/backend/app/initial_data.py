import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.db import engine, init_db
from app.core.models.user import User
from app.core.security import get_password_hash
from app.core.config.settings import settings
from app.core.config.constants import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    with Session(engine) as session:
        init_db(session)
        
        # Check if admin user exists
        admin = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()
        
        if not admin:
            # Create admin user directly using SQLModel
            admin = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="Admin User",
                is_active=True,
                role=UserRole.ADMIN,
                created_at=datetime.now(timezone.utc)
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            logger.info(f"Created admin user: {admin.email}")


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
