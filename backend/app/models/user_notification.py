from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from backend.app.db.base import Base


class UserNotification(Base):
    """Notification delivered to a user."""

    __tablename__ = "user_notification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=True, index=True)
    comment_id = Column(Integer, ForeignKey("comment.id"), nullable=True, index=True)
    notification_type = Column(String(32), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(String(512), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
