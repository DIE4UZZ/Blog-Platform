"""
schemas/social.py —— 社交功能相关请求数据模式

包含关注/取关、通知已读等接口的请求体定义。
"""

from typing import List, Optional

from pydantic import BaseModel


class FollowActionRequest(BaseModel):
    """关注/取关操作请求体。

    Attributes:
        target_user_id (int): 目标用户 ID（要关注或取关的用户），必填。
        action (str): 操作类型，"follow"（关注）或 "unfollow"（取关）。
    """

    target_user_id: int     # 目标用户 ID，必填
    action: str             # 操作类型："follow" 或 "unfollow"


class NotificationReadRequest(BaseModel):
    """标记通知已读请求体。

    支持两种模式：
      1. 全部已读：read_all=True，忽略 notification_ids
      2. 指定已读：read_all=False，notification_ids 填写要标记的通知 ID 列表

    Attributes:
        read_all (bool): 是否将所有未读通知标记为已读，默认 False。
        notification_ids (Optional[List[int]]): 要标记为已读的通知 ID 列表，
            read_all=False 时必填。
    """

    read_all: bool = False                          # 是否全部已读
    notification_ids: Optional[List[int]] = None   # 指定通知 ID 列表
