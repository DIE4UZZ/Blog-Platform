from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from backend.app.db.base import Base


class ArticleReadLater(Base):
    """Track articles saved for later by users."""

    __tablename__ = "article_read_later"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_read_later_user_article"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=False, index=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
