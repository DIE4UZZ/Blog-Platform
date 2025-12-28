from pydantic import BaseModel


class CommentCreateRequest(BaseModel):
    """Request body for creating a comment.

    Attributes:
        article_id (int): Article id.
        content (str): Comment content.
        parent_id (int): Parent comment id.
    """

    article_id: int
    content: str
    parent_id: int = 0
