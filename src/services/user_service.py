from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas.user_schema import UserCreate, UserUpdate
from security import get_password_hash


class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    @staticmethod
    async def get_user_by_uuid(
        db: AsyncSession, user_uuid: str
    ) -> User | None:
        result = await db.execute(
            select(User).filter(User.uuid == str(user_uuid))
        )
        return result.scalars().first()

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
        if user_in.password != user_in.password_confirmation:
            raise HTTPException(
                status_code=400, detail="Passwords do not match"
            )
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
        db: AsyncSession, db_user: User, user_in: UserUpdate
    ) -> User:
        update_data = user_in.model_dump(exclude_unset=True)
        if (
            "password" in update_data
            and "password_confirmation" in update_data
        ):
            if update_data["password"] != update_data["password_confirmation"]:
                raise HTTPException(
                    status_code=400, detail="Passwords do not match"
                )
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
    async def delete_user(db: AsyncSession, user_uuid: str) -> User | None:
        result = await db.execute(
            select(User).filter(User.uuid == str(user_uuid))
        )
        db_user = result.scalars().first()
        if db_user:
            await db.delete(db_user)
            await db.commit()
        return db_user
