from pydantic import BaseModel, Field


class ArticlePublishRequest(BaseModel):
    """Request body for publishing an article.

    Attributes:
        title (str): Article title.
        content (str): Markdown content.
        category (str): Article category.
        tags (str | None): Comma-separated tags.
        status (str): draft/published.
    """

    title: str
    content: str
    category: str
    tags: str | None = None
    status: str = Field(default="published")


class ArticleEditRequest(BaseModel):
    """Request body for editing an article.

    Attributes:
        article_id (int): Article id.
        title (str): Article title.
        content (str): Markdown content.
        category (str): Article category.
        tags (str | None): Comma-separated tags.
        status (str): draft/published.
    """

    article_id: int
    title: str
    content: str
    category: str
    tags: str | None = None
    status: str = Field(default="published")


class ArticleActionRequest(BaseModel):
    """Request body for like/collect actions.

    Attributes:
        article_id (int): Article id.
        action (str): Action name (like/unlike/collect/uncollect).
    """

    article_id: int
    action: str
