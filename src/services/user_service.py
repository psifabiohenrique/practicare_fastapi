from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from models import User
from schemas.user import UserCreate, UserUpdate
from security import get_password_hash


class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_uuid(db: Session, user_uuid: str) -> User | None:
        return db.query(User).filter(User.uuid == str(user_uuid)).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
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
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db: Session, db_user: User, user_in: UserUpdate) -> User:
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
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def delete_user(db: Session, user_uuid: str) -> User | None:
        db_user = db.query(User).filter(User.uuid == str(user_uuid)).first()
        if db_user:
            db.delete(db_user)
            db.commit()
        return db_user
