from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from backend.app.db.base import Base


class ArticleCollect(Base):
    """Track user collections on articles.

    Attributes:
        id (int): Primary key.
        user_id (int): User id.
        article_id (int): Article id.
        create_time (datetime): Create time.
    """

    __tablename__ = "article_collect"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_collect_user_article"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=False, index=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)

