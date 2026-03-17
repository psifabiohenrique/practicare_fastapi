from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models import User
from src.schemas.user_schema import UserCreate, UserUpdate
from src.security import get_password_hash


class UserService:
    @staticmethod
    async def get_user_by_uuid(db: AsyncSession, user_uuid: str) -> User:
        result = await db.execute(
            select(User).filter(User.uuid == str(user_uuid))
        )
        user = result.scalars().first()
        if not user:
            raise NotFoundError("User not found")
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    @staticmethod
    async def get_users(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        # Check if email exists
        existing_user = await UserService.get_user_by_email(db, user_in.email)
        if existing_user:
            raise ConflictError("User with this email already exists")

        if user_in.password != user_in.password_confirmation:
            raise ValidationError("Passwords do not match")

        db_user = User(
            email=user_in.email,
            name=user_in.name,
            hashed_password=get_password_hash(user_in.password),
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def update_user(
        db: AsyncSession, user_uuid: str, user_in: UserUpdate
    ) -> User:
        db_user = await UserService.get_user_by_uuid(db, user_uuid)

        update_data = user_in.model_dump(exclude_unset=True)
        if (
            "password" in update_data
            and "password_confirmation" in update_data
        ):
            if update_data["password"] != update_data["password_confirmation"]:
                raise ValidationError("Passwords do not match")
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def delete_user(db: AsyncSession, user_uuid: str) -> User:
        db_user = await UserService.get_user_by_uuid(db, user_uuid)
        await db.delete(db_user)
        await db.commit()
        return db_user
