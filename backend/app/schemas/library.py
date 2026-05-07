from pydantic import BaseModel, Field


class ReadLaterActionRequest(BaseModel):
    article_id: int
    action: str = Field(description="save or remove")
