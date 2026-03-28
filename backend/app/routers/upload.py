from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.models.user import User

router = APIRouter()

UPLOAD_DIR = Path("backend/uploads")
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/upload/image")
async def upload_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传文章图片并返回可访问地址。"""

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPG、JPEG、WebP、GIF 图片")

    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)

    return success_response(
        {"url": f"/uploads/{filename}", "file_name": filename},
        message="上传成功",
    )
