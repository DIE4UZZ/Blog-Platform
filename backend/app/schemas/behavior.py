"""
schemas/behavior.py —— 用户行为上报请求数据模式

定义前端上报用户行为事件的请求体格式。
前端通过批量上报（report-batch）或单条上报（report）接口发送行为数据。
"""

from typing import List, Optional

from pydantic import BaseModel


class BehaviorReportRequest(BaseModel):
    """单条行为上报请求体。

    Attributes:
        article_id (Optional[int]): 相关文章 ID，搜索/页面浏览行为可为空。
        behavior_type (str): 行为类型，如 "read"/"like"/"collect"/"search"/"page_view"。
        read_duration (Optional[int]): 阅读时长（秒），仅 read 行为填写。
        scroll_depth (Optional[float]): 滚动深度（0.0~1.0），仅 read 行为填写。
        keyword (Optional[str]): 搜索关键词或页面路径，仅 search/page_view 行为填写。
    """

    article_id: Optional[int] = None        # 相关文章 ID
    behavior_type: str                      # 行为类型，必填
    read_duration: Optional[int] = None     # 阅读时长（秒）
    scroll_depth: Optional[float] = None    # 滚动深度（0.0~1.0）
    keyword: Optional[str] = None           # 搜索词或页面路径


class BehaviorBatchReportRequest(BaseModel):
    """批量行为上报请求体。

    前端将多条行为事件打包成一个请求发送，减少 HTTP 请求次数。

    Attributes:
        items (List[BehaviorReportRequest]): 行为事件列表，最多 20 条。
    """

    items: List[BehaviorReportRequest]  # 行为事件列表
