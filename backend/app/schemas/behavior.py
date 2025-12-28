from pydantic import BaseModel


class BehaviorReportRequest(BaseModel):
    """Request body for reporting user behavior.

    Attributes:
        user_id (int | None): User id, optional.
        article_id (int | None): Article id.
        behavior_type (str): Behavior type.
        read_duration (int | None): Read duration in seconds.
        scroll_depth (float | None): Scroll depth 0-1.
        keyword (str | None): Search keyword.
    """

    user_id: int | None = None
    article_id: int | None = None
    behavior_type: str
    read_duration: int | None = None
    scroll_depth: float | None = None
    keyword: str | None = None
