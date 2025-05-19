from sqlmodel import create_engine, Session, select

from app.core.config.settings import settings
from app.core.models.user import User
from app.core.security import get_password_hash
from app.core.config.constants import UserRole
from datetime import datetime, timezone

# Create engine with the SQLALCHEMY_DATABASE_URI property
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

# make sure all SQLAlchemy models are imported before initializing DB
# otherwise, SQLAlchemy might fail to initialize relationships properly

def get_session():
    """Dependency for getting a SQLModel session"""
    with Session(engine) as session:
        yield session

def init_db(session: Session) -> None:
    """Initialize database with first superuser if needed"""
    # Tables should be created with Alembic migrations
    # SQLModel.metadata.create_all(engine)
    
    # Check if admin user exists
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    
    if not user:
        admin = User(
            email=settings.FIRST_SUPERUSER,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Admin User",
            is_active=True,
            role=UserRole.ADMIN.value,
            created_at=datetime.now(timezone.utc)
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
