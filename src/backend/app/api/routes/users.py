import uuid
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, delete, func, select

from app.core.crud import user as crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config.settings import settings
from app.core.security import get_password_hash, verify_password
from app.core.models.user import (
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.core.utils import generate_new_account_email, send_email

router = APIRouter()

# Create an annotated dependency for superuser
SuperUser = Annotated[User, Depends(get_current_active_superuser)]

# Helper function to convert User model to UserPublic
def user_to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.user_id,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        role=user.role,
        preferences=user.preferences,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=list(user.permissions)
    )

@router.get(
    "/",
    response_model=UsersPublic,
)
def read_users(
    session: SessionDep, 
    current_user: SuperUser,
    skip: int = 0, 
    limit: int = 100
) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users_db = session.exec(statement).all()
    
    # Convert users to UserPublic models
    users_public = [user_to_public(user) for user in users_db]

    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", 
    response_model=UserPublic
)
def create_user(
    session: SessionDep, 
    user_in: UserCreate,
    current_user: SuperUser
) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    
    # Convert User model to UserPublic
    return user_to_public(user)


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    session: SessionDep, 
    user_in: UserUpdateMe, 
    current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    # Convert User model to UserPublic
    return user_to_public(current_user)


@router.patch("/me/password", response_model=Message)
def update_password_me(
    session: SessionDep, 
    body: UpdatePassword, 
    current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return user_to_public(current_user)


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user_to_public(user)


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, 
    session: SessionDep, 
    current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.exec(select(User).where(User.user_id == str(user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        return user_to_public(user)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user_to_public(user)


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
)
def update_user(
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: SuperUser
) -> Any:
    """
    Update a user.
    """

    db_user = session.exec(select(User).where(User.user_id == str(user_id))).first()
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != db_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return user_to_public(db_user)


@router.delete("/{user_id}")
def delete_user(
    session: SessionDep, 
    user_id: uuid.UUID,
    current_user: SuperUser
) -> Any:
    """
    Delete a user.
    """
    user = session.exec(select(User).where(User.user_id == str(user_id))).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
