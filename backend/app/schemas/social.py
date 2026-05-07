from pydantic import BaseModel, Field


class FollowActionRequest(BaseModel):
    target_user_id: int
    action: str = Field(description="follow or unfollow")


class NotificationReadRequest(BaseModel):
    notification_ids: list[int] = Field(default_factory=list)
    read_all: bool = False
