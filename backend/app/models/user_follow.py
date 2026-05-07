from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from backend.app.db.base import Base


class UserFollow(Base):
    """Track follow relationships between users."""

    __tablename__ = "user_follow"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follow_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    following_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
