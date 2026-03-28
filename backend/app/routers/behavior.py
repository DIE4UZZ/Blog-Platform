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
    return UserBehavior(
        user_id=user.id if user else None,
        article_id=payload.article_id,
        behavior_type=payload.behavior_type,
        read_duration=payload.read_duration,
        scroll_depth=payload.scroll_depth,
        keyword=payload.keyword,
        create_time=datetime.utcnow(),
    )


@router.post("/behavior/report")
def report_behavior(
    payload: BehaviorReportRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    db.add(_build_behavior(current_user, payload))
    db.commit()
    return success_response({}, message="上报成功")


@router.post("/behavior/report-batch")
def report_behavior_batch(
    payload: BehaviorBatchReportRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    for item in payload.items:
        db.add(_build_behavior(current_user, item))
    db.commit()
    return success_response({"count": len(payload.items)}, message="批量上报成功")
