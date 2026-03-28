from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from backend.app.db.base import Base


class UserBehavior(Base):
    """User behavior log model.

    Attributes:
        id (int): Primary key.
        user_id (int | None): User id, nullable for guest.
        article_id (int | None): Article id when applicable.
        behavior_type (str): Behavior type (read/like/collect/comment/search).
        read_duration (int | None): Read duration in seconds.
        scroll_depth (float | None): Scroll depth 0-1.
        keyword (str | None): Search keyword.
        create_time (datetime): Create time.
    """

    __tablename__ = "user_behavior"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=True, index=True)
    behavior_type = Column(String(32), nullable=False, index=True)
    read_duration = Column(Integer, nullable=True)
    scroll_depth = Column(Float, nullable=True)
    keyword = Column(String(255), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)

