from app.db.base import Base
from app.db.session import engine
from app.models.article import Article
from app.models.article_collect import ArticleCollect
from app.models.article_like import ArticleLike
from app.models.behavior import UserBehavior
from app.models.comment import Comment
from app.models.recommendation import Recommendation
from app.models.user import User


def init_db():
    """Create database tables based on ORM models.

    Returns:
        None: No return value.
    """

    Base.metadata.create_all(bind=engine)
