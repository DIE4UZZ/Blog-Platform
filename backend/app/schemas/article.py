"""
schemas/article.py —— 文章相关请求数据模式

定义文章发布、编辑等接口的请求体校验模型。
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class PublishArticleRequest(BaseModel):
    """发布文章请求体。

    Attributes:
        title (str): 文章标题，1-255 字符。
        content (str): 文章正文（Markdown 格式），不能为空。
        summary (Optional[str]): 文章摘要，可为空，前端可自动截取正文前 N 字。
        category (Optional[str]): 文章分类，如 "技术"、"生活"。
        tags (Optional[str]): 标签，逗号分隔，如 "Python,FastAPI"。
        status (str): 发布状态，"draft"（草稿）或 "published"（发布），默认 "published"。
    """

    title: str                          # 文章标题，必填
    content: str                        # 文章正文，必填
    summary: Optional[str] = None       # 摘要，选填
    category: Optional[str] = None      # 分类，选填
    tags: Optional[str] = None          # 标签，选填
    status: str = "published"           # 发布状态，默认直接发布

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """校验标题：去除首尾空格，检查长度（1-255）。"""
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        if len(value) > 255:
            raise ValueError("标题长度不能超过 255 字符")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """校验发布状态：只允许 draft 或 published。"""
        if value not in {"draft", "published"}:
            raise ValueError("status 只能是 draft 或 published")
        return value


class EditArticleRequest(BaseModel):
    """编辑文章请求体。

    与 PublishArticleRequest 相比，增加了 article_id 字段用于定位要编辑的文章。

    Attributes:
        article_id (int): 要编辑的文章 ID，必填。
        title (str): 新标题。
        content (str): 新正文。
        summary (Optional[str]): 新摘要。
        category (Optional[str]): 新分类。
        tags (Optional[str]): 新标签。
        status (str): 新状态，"draft" 或 "published"。
    """

    article_id: int                     # 文章 ID，必填
    title: str                          # 新标题
    content: str                        # 新正文
    summary: Optional[str] = None       # 新摘要
    category: Optional[str] = None      # 新分类
    tags: Optional[str] = None          # 新标签
    status: str = "published"           # 新状态


# 别名：兼容 routers/article.py 中的导入名称
ArticlePublishRequest = PublishArticleRequest
ArticleEditRequest = EditArticleRequest


class ArticleActionRequest(BaseModel):
    """文章互动操作请求体（点赞/取消点赞/收藏/取消收藏）。

    Attributes:
        article_id (int): 目标文章 ID，必填。
        action (str): 操作类型，如 "like"/"unlike"/"collect"/"uncollect"。
    """

    article_id: int     # 目标文章 ID，必填
    action: str         # 操作类型，必填
