from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from app.db.base import Base


class Comment(Base):
    """Comment model for article discussion.

    Attributes:
        id (int): Primary key.
        article_id (int): Article id.
        user_id (int): User id.
        content (str): Comment text.
        parent_id (int): Parent comment id.
        create_time (datetime): Create time.
    """

    __tablename__ = "comment"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, nullable=False, default=0)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
