"""
schemas/comment.py —— 评论相关请求数据模式
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class CommentRequest(BaseModel):
    """提交评论或回复请求体。

    Attributes:
        article_id (int): 评论所属文章 ID，必填。
        content (str): 评论正文，1-2000 字符。
        parent_id (Optional[int]): 父评论 ID，顶级评论不填，回复时填写被回复的评论 ID。
    """

    article_id: int                     # 所属文章 ID，必填
    content: str                        # 评论内容，必填
    parent_id: Optional[int] = None     # 父评论 ID，顶级评论为 None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """校验评论内容：去除首尾空格，检查长度（1-2000）。"""
        value = value.strip()
        if not value:
            raise ValueError("评论内容不能为空")
        if len(value) > 2000:
            raise ValueError("评论内容不能超过 2000 字符")
        return value


# 别名：兼容 routers/comment.py 中的导入名称
CommentCreateRequest = CommentRequest
