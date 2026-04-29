import logging
from uuid import UUID

from fastapi import APIRouter, Request, status

from src.core.rate_limit import limiter
from src.routers.deps import CurrentUser, SessionDB
from src.schemas.user_schema import UserCreate, UserRead, UserUpdate
from src.services.user_service import UserService
from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_MEDIUM)
async def create_user(
    *, request: Request, db: SessionDB, user_in: UserCreate
) -> any:
    logger.info(f"Criando novo usuário: {user_in.email}")
    return await UserService.create_user(db, user_in=user_in)


@router.get("", response_model=list[UserRead])
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
    return await UserService.get_user_by_uuid(db, user_uuid=str(user_uuid))


@router.patch("/{user_uuid}", response_model=UserRead)
@limiter.limit(settings.RATE_LIMIT_MEDIUM)
async def update_user(
    *,
    request: Request,
    db: SessionDB,
    user_uuid: UUID,
    user_in: UserUpdate,
    current_user: CurrentUser,
) -> any:
    logger.info(
        f"Atualizando usuário: {user_uuid}",
        extra={
            "user_uuid": str(user_uuid),
            "updated_by": str(current_user.uuid),
        },
    )
    return await UserService.update_user(
        db, user_uuid=str(user_uuid), user_in=user_in
    )


@router.delete("/{user_uuid}", response_model=UserRead)
@limiter.limit(settings.RATE_LIMIT_MEDIUM)
async def delete_user(
    *,
    request: Request,
    db: SessionDB,
    user_uuid: UUID,
    current_user: CurrentUser,
) -> any:
    logger.info(
        f"Excluindo usuário: {user_uuid}",
        extra={
            "user_uuid": str(user_uuid),
            "deleted_by": str(current_user.uuid),
        },
    )
    return await UserService.delete_user(db, user_uuid=str(user_uuid))
