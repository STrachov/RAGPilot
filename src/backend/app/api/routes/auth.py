from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlmodel import select, Session

from app.core.crud import user as crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core import security
from app.core.config.settings import settings
from app.core.config.constants import UserRole
from app.core.models.refresh_token import RefreshToken
from app.core.models.user import Token, UserPublic, User, UserRegister, UpdatePassword
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logger import auth_logger

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDep
):
    """OAuth2 compatible token login, get an access token for future requests"""
    auth_logger.info(f"Login attempt for user: {form_data.username}")
    
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        auth_logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        auth_logger.warning(f"Login attempt for inactive user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Account is inactive"
        )
    
    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.user_id),
        expires_delta=access_token_expires,
        role=user.role,
        permissions=list(user.permissions)
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_value = create_access_token(
        subject=str(user.user_id),
        expires_delta=refresh_token_expires,
    )
    refresh_token = RefreshToken(
        user_id=user.user_id,
        token=refresh_token_value,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    db.add(refresh_token)
    db.commit()
    
    auth_logger.info(f"User {user.email} (ID: {user.user_id}) logged in successfully")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        message="Successfully logged in",
        role=user.role,
        permissions=list(user.permissions)
    )


@router.post("/login/web")
async def login_web(
    session: SessionDep, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> JSONResponse:
    """
    OAuth2 compatible token login that returns HTTP-only cookies for web clients
    """
    auth_logger.info(f"Web login attempt for user: {form_data.username}")
    
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        auth_logger.warning(f"Failed web login attempt for user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        auth_logger.warning(f"Web login attempt for inactive user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = security.create_access_token(
        subject=str(user.user_id), 
        expires_delta=access_token_expires,
        role=user.role,
        permissions=list(user.permissions)
    )
    refresh_token = security.create_access_token(
        subject=str(user.user_id), 
        expires_delta=refresh_token_expires
    )

    # Store refresh token in the database
    new_refresh_token = RefreshToken(
        user_id=user.user_id,
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    session.add(new_refresh_token)
    session.commit()

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="strict")
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="strict")
    
    auth_logger.info(f"User {user.email} (ID: {user.user_id}) web login successful")
    return response


@router.post("/refresh", response_model=Token)
async def refresh_token_api(
    refresh_token: str, 
    db: SessionDep
):
    """Get a new access token using a refresh token"""
    auth_logger.info("Token refresh attempt")
    
    # Find the refresh token in the database
    token_record = db.exec(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
    ).first()
    
    if not token_record:
        auth_logger.warning("Token refresh attempt with invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the user associated with the token
    user = db.exec(select(User).where(User.user_id == token_record.user_id)).first()
    if not user or not user.is_active:
        auth_logger.warning(f"Token refresh attempt for inactive or deleted user ID: {token_record.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.user_id),
        expires_delta=access_token_expires,
        role=user.role,
        permissions=list(user.permissions)
    )
    
    auth_logger.info(f"Token refreshed successfully for user {user.email} (ID: {user.user_id})")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        message="Token refreshed successfully",
        role=user.role,
        permissions=list(user.permissions)
    )


@router.post("/refresh/web")
async def refresh_web_token(
    session: SessionDep, 
    refresh_token: str = Cookie(None)
):
    """
    Issues a new access token using a valid, non-revoked refresh token from cookies.
    """
    auth_logger.info("Web token refresh attempt")
    
    if not refresh_token:
        auth_logger.warning("Web token refresh attempt without refresh token")
        raise HTTPException(status_code=403, detail="No refresh token provided")

    # Retrieve token and check if it's revoked or expired
    token_entry = session.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if not token_entry:
        auth_logger.warning("Web token refresh attempt with invalid token")
        raise HTTPException(status_code=403, detail="Invalid refresh token")

    if token_entry.revoked:
        auth_logger.warning("Web token refresh attempt with revoked token")
        raise HTTPException(status_code=403, detail="Refresh token has been revoked")

    if token_entry.expires_at < datetime.now(timezone.utc):
        auth_logger.warning("Web token refresh attempt with expired token")
        raise HTTPException(status_code=403, detail="Refresh token has expired")

    # Get the user associated with the token
    user = session.exec(select(User).where(User.user_id == token_entry.user_id)).first()

    # Generate new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=str(token_entry.user_id), 
        expires_delta=access_token_expires,
        role=user.role if user else UserRole.USER,
        permissions=list(user.permissions) if user else []
    )

    response = JSONResponse(content={"message": "Token refreshed successfully"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict"
    )
    
    auth_logger.info(f"Web token refreshed successfully for user ID: {token_entry.user_id}")
    return response


@router.post("/register", response_model=Token)
async def register(
    user_data: UserRegister, 
    db: SessionDep
):
    """Register a new user"""
    auth_logger.info(f"Registration attempt for email: {user_data.email}")
    
    # Check if user with this email already exists
    existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        auth_logger.warning(f"Registration attempt with existing email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(new_user.user_id),
        expires_delta=access_token_expires,
        role=new_user.role,
        permissions=list(new_user.permissions)
    )
    
    auth_logger.info(f"User registered successfully: {new_user.email} (ID: {new_user.user_id})")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        message="User registered successfully",
        role=new_user.role,
        permissions=list(new_user.permissions)
    )


@router.post("/password/update", response_model=UserPublic)
async def update_password(
    password_data: UpdatePassword,
    current_user: CurrentUser,
    db: SessionDep
):
    """Update user password"""
    auth_logger.info(f"Password update attempt for user: {current_user.email} (ID: {current_user.user_id})")
    
    if not verify_password(password_data.current_password, current_user.hashed_password):
        auth_logger.warning(f"Password update failed - incorrect current password: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # Revoke all refresh tokens
    tokens = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.user_id,
            RefreshToken.revoked == False
        )
    ).all()
    
    for token in tokens:
        token.revoked = True
        db.add(token)
    
    db.commit()
    
    auth_logger.info(f"Password updated successfully for user: {current_user.email}")
    
    return current_user


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    db: SessionDep
):
    """Logout - revoke all refresh tokens for the user"""
    auth_logger.info(f"Logout for user: {current_user.email} (ID: {current_user.user_id})")
    
    tokens = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.user_id,
            RefreshToken.revoked == False
        )
    ).all()
    
    for token in tokens:
        token.revoked = True
        db.add(token)
    
    db.commit()
    
    auth_logger.info(f"User logged out successfully: {current_user.email}")
    
    return {"message": "Successfully logged out"}


@router.post("/logout/web")
async def logout_web(
    response: Response,
    session: SessionDep,
    refresh_token: str = Cookie(None)
):
    """
    Logs out the user by marking the refresh token as revoked and clearing cookies.
    """
    auth_logger.info("Web logout attempt")
    
    if not refresh_token:
        auth_logger.warning("Web logout attempt with no refresh token")
        raise HTTPException(status_code=400, detail="No refresh token provided")

    # Find the refresh token and mark it as revoked
    token_entry = session.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if token_entry:
        token_entry.revoked = True  # Blacklist the token
        session.commit()
        auth_logger.info(f"Web logout successful for user ID: {token_entry.user_id}")

    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return JSONResponse(content={"message": "Logout successful"})


@router.post("/test-token", response_model=None)
async def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token and return detailed validation information
    """
    return {
        "status": "valid",
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "role": current_user.role,
        "permissions": list(current_user.permissions),
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "message": "Token is valid and active"
    }