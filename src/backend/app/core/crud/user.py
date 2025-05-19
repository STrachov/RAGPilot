from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Session, select

from app.core.models.user import User, UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.config.constants import UserRole


def get_user_by_email(session: Session, email: EmailStr) -> Optional[User]:
    """Get a user by email"""
    return session.exec(select(User).where(User.email == email)).first()


def authenticate(session: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password"""
    user = get_user_by_email(session=session, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(session: Session, user_create: UserCreate) -> User:
    """Create a new user"""
    # Create a new user with the provided data
    hashed_password = get_password_hash(user_create.password)
    
    # Handle is_superuser legacy property (which maps to admin role)
    is_admin = getattr(user_create, "is_superuser", False)
    
    # Create the user and convert the SQLModel to a proper User object
    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        is_active=user_create.is_active,
        role=UserRole.ADMIN if is_admin else user_create.role,
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def update_user(session: Session, db_user: User, user_in: UserUpdate) -> User:
    """Update user data"""
    # Get the data to update as a dictionary, excluding unset fields
    user_data = user_in.model_dump(exclude_unset=True)
    
    # If password is being updated, hash it
    if "password" in user_data:
        password = user_data.pop("password")
        user_data["hashed_password"] = get_password_hash(password)
    
    # Update the timestamp
    user_data["updated_at"] = datetime.now(timezone.utc)
    
    # Update the user object with the new data
    for field, value in user_data.items():
        setattr(db_user, field, value)
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user 