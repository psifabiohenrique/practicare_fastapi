from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from routers.deps import get_current_user
from schemas.user import UserCreate, UserRead, UserUpdate
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

SessionDB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(*, db: SessionDB, user_in: UserCreate) -> any:
    user = await UserService.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    return await UserService.create_user(db, user_in=user_in)


@router.get("/", response_model=list[UserRead])
async def read_users(
    current_user: CurrentUser,
    db: SessionDB,
    skip: int = 0,
    limit: int = 100,
) -> any:
    return await UserService.get_users(db, skip=skip, limit=limit)


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user: CurrentUser,
) -> any:
    return current_user


@router.get("/{user_uuid}", response_model=UserRead)
async def read_user_by_uuid(
    user_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    user = await UserService.get_user_by_uuid(db, user_uuid=str(user_uuid))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_uuid}", response_model=UserRead)
async def update_user(
    *,
    db: SessionDB,
    user_uuid: UUID,
    user_in: UserUpdate,
    current_user: CurrentUser,
) -> any:
    user = await UserService.get_user_by_uuid(db, user_uuid=str(user_uuid))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await UserService.update_user(db, db_user=user, user_in=user_in)


@router.delete("/{user_uuid}", response_model=UserRead)
async def delete_user(
    *,
    db: SessionDB,
    user_uuid: UUID,
    current_user: CurrentUser,
) -> any:
    user = await UserService.delete_user(db, user_uuid=str(user_uuid))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
