from uuid import uuid4

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, DateTime, ForeignKey, Index, func

from src.database import Base


class AuthSession(Base):
    tablename = "sessions"

    uuid = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_uuid = Column(
        SQLUUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sessions_user_uuid", "user_uuid"),
        Index("ix_sessions_expires_at", "expires_at"),
    )
