from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from passlib.context import CryptContext

from app.core.config.settings import settings
from app.core.config.constants import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any, 
    expires_delta: timedelta,
    role: UserRole = UserRole.USER,
    permissions: Optional[List[str]] = None
) -> str:
    """Create JWT token with user information including role and permissions"""
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode: Dict[str, Any] = {
        "exp": expire, 
        "sub": str(subject),
        "role": role,
    }
    
    if permissions:
        to_encode["permissions"] = permissions
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
