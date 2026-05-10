"""
schemas/library.py —— 书库功能相关请求数据模式

包含稍后阅读（书签）操作的请求体定义。
"""

from pydantic import BaseModel


class ReadLaterActionRequest(BaseModel):
    """稍后阅读操作请求体。

    Attributes:
        article_id (int): 目标文章 ID，必填。
        action (str): 操作类型，"save"（添加到稍后阅读）或 "remove"（从稍后阅读移除）。
    """

    article_id: int     # 目标文章 ID，必填
    action: str         # 操作类型："save" 或 "remove"
