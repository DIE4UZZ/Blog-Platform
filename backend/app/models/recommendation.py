from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.db.base import Base


class Recommendation(Base):
    """Recommendation record model.

    Attributes:
        id (int): Primary key.
        user_id (int | None): User id, nullable for guest.
        article_id (int): Article id.
        recommend_type (str): Recommendation type.
        recommend_score (float): Recommendation score.
        is_clicked (bool): Click status.
        create_time (datetime): Create time.
    """

    __tablename__ = "recommendation"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=False, index=True)
    recommend_type = Column(String(32), nullable=False)
    recommend_score = Column(Float, nullable=False, default=0.0)
    is_clicked = Column(Boolean, nullable=False, default=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
