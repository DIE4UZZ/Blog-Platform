"""
routers/upload.py —— 文件上传路由模块

提供图片上传接口，供文章编辑器使用：
  - POST /upload/image : 上传图片，返回可访问的 URL

安全限制：
  - 仅允许登录用户上传（需要 JWT 认证）
  - 仅支持 PNG、JPG、JPEG、WebP、GIF 格式
  - 单文件大小上限：5MB
  - 文件名使用 UUID 随机生成，防止路径遍历攻击

存储路径：backend/uploads/<uuid>.<ext>
访问路径：/uploads/<uuid>.<ext>（由 main.py 挂载静态文件目录）
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.models.user import User

router = APIRouter()

# 图片存储目录（相对于项目根目录）
UPLOAD_DIR = Path("backend/uploads")

# 允许上传的图片格式（小写后缀）
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# 单文件大小上限：5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/upload/image")
async def upload_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传文章图片并返回可访问地址。

    处理流程：
      1. 校验文件格式（后缀名白名单）
      2. 读取文件内容，校验文件大小
      3. 生成 UUID 文件名（防止重名和路径遍历）
      4. 保存到 UPLOAD_DIR 目录
      5. 返回可访问的 URL 路径

    Args:
        image: 上传的图片文件（multipart/form-data）。
        current_user: 当前登录用户（需要 JWT 认证）。

    Returns:
        成功响应，data 包含：
          - url: 图片访问路径（如 /uploads/abc123.jpg）
          - file_name: 保存的文件名（如 abc123.jpg）

    Raises:
        HTTPException(400): 文件格式不支持、文件为空或超过大小限制时抛出。
    """
    # 校验文件格式（后缀名白名单）
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPG、JPEG、WebP、GIF 图片")

    # 读取文件内容并校验大小
    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    # 创建上传目录（若不存在）
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 使用 UUID 生成随机文件名（防止重名和路径遍历攻击）
    filename = f"{uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)

    return success_response(
        {"url": f"/uploads/{filename}", "file_name": filename},
        message="上传成功",
    )
