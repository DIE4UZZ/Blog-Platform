from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import success_response
from app.db.session import get_db
from app.models.behavior import UserBehavior
from app.models.user import User
from app.schemas.behavior import BehaviorReportRequest

router = APIRouter()


@router.post("/behavior/report")
def report_behavior(
    payload: BehaviorReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report user behavior data.

    Args:
        payload (BehaviorReportRequest): Behavior report payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response.
    """

    behavior = UserBehavior(
        user_id=current_user.id,
        article_id=payload.article_id,
        behavior_type=payload.behavior_type,
        read_duration=payload.read_duration,
        scroll_depth=payload.scroll_depth,
        keyword=payload.keyword,
        create_time=datetime.utcnow(),
    )
    db.add(behavior)
    db.commit()
    return success_response({}, message="上报成功")
