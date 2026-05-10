"""
routers/behavior.py —— 用户行为上报路由模块

提供前端上报用户行为事件的接口：
  - POST /behavior/report       : 单条行为上报
  - POST /behavior/report-batch : 批量行为上报（推荐使用，减少 HTTP 请求次数）

行为数据用途：
  1. 推荐算法：根据用户的阅读/点赞/收藏/搜索行为计算兴趣偏好
  2. 数据分析：统计 PV/UV、阅读时长、滚动深度等指标
  3. 用户画像：分析用户活跃时段、偏好分类等

支持匿名上报：
  - 已登录用户：user_id = 当前用户 ID
  - 未登录用户：user_id = None（匿名行为，不影响个性化推荐）
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.deps import get_optional_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.behavior import UserBehavior
from backend.app.models.user import User
from backend.app.schemas.behavior import BehaviorBatchReportRequest, BehaviorReportRequest

router = APIRouter()


def _build_behavior(user: User | None, payload: BehaviorReportRequest) -> UserBehavior:
    """根据请求体构建 UserBehavior ORM 对象。

    Args:
        user (User | None): 当前用户，未登录时为 None。
        payload (BehaviorReportRequest): 行为上报请求体。

    Returns:
        UserBehavior: 待插入数据库的行为记录对象。
    """
    return UserBehavior(
        user_id=user.id if user else None,          # 未登录用户 user_id 为 None
        article_id=payload.article_id,              # 相关文章 ID（搜索行为可为 None）
        behavior_type=payload.behavior_type,        # 行为类型：read/like/collect/search/page_view
        read_duration=payload.read_duration,        # 阅读时长（秒），仅 read 行为有值
        scroll_depth=payload.scroll_depth,          # 滚动深度（0.0~1.0），仅 read 行为有值
        keyword=payload.keyword,                    # 搜索词或页面路径
        create_time=datetime.utcnow(),
    )


@router.post("/behavior/report")
def report_behavior(
    payload: BehaviorReportRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """单条行为上报接口。

    前端在用户执行单个行为时调用，例如：
      - 用户搜索关键词时上报 search 行为
      - 用户离开文章页面时上报 read 行为（含阅读时长和滚动深度）

    Args:
        payload (BehaviorReportRequest): 行为数据，包含行为类型和相关参数。
        db (Session): 数据库会话。
        current_user (User | None): 当前用户，未登录时为 None（支持匿名上报）。

    Returns:
        成功响应，data 为空对象。
    """
    db.add(_build_behavior(current_user, payload))
    db.commit()
    return success_response({}, message="上报成功")


@router.post("/behavior/report-batch")
def report_behavior_batch(
    payload: BehaviorBatchReportRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """批量行为上报接口（推荐使用）。

    前端将多条行为事件打包成一个请求发送，减少 HTTP 请求次数。
    适用场景：
      - 页面卸载时批量上报本次会话的所有行为
      - 定时批量上报（如每 30 秒上报一次）

    Args:
        payload (BehaviorBatchReportRequest): 批量行为数据，包含 items 列表。
        db (Session): 数据库会话。
        current_user (User | None): 当前用户，未登录时为 None。

    Returns:
        成功响应，data 包含 count（成功上报的行为数量）。
    """
    # 批量插入所有行为记录（一次 commit，减少数据库事务开销）
    for item in payload.items:
        db.add(_build_behavior(current_user, item))
    db.commit()
    return success_response({"count": len(payload.items)}, message="批量上报成功")
