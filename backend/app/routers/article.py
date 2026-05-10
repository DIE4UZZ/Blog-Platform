"""
routers/article.py —— 文章路由模块

提供文章的增删改查接口：
  - POST   /article/publish  : 发布新文章（登录必须）
  - PUT    /article/edit     : 编辑已有文章（作者或管理员）
  - DELETE /article/delete   : 软删除文章（作者或管理员）
  - GET    /article/detail   : 获取文章详情（支持匿名访问）
  - GET    /article/list     : 获取文章列表（支持分类/标签/关键词筛选）
  - GET    /article/my-list  : 获取当前用户的文章列表（含草稿）

发布文章时的联动操作：
  1. 调用 push_new_article_recommendations：将新文章推送给相关用户的推荐列表
  2. 调用 create_new_article_notifications：通知关注该作者的粉丝
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from markdown import markdown
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user, get_optional_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_read_later import ArticleReadLater
from backend.app.models.article_like import ArticleLike
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow
from backend.app.routers.recommend import push_new_article_recommendations
from backend.app.routers.social import create_new_article_notifications
from backend.app.schemas.article import ArticleEditRequest, ArticlePublishRequest

router = APIRouter()


def build_summary(content: str, limit: int = 120) -> str:
    """从文章正文中提取摘要（取前 N 个字符）。

    处理逻辑：
      1. 将换行符替换为空格，使摘要在一行内展示
      2. 去除首尾空格
      3. 截取前 limit 个字符

    Args:
        content (str): 文章正文（Markdown 格式）。
        limit (int): 摘要最大字符数，默认 120。

    Returns:
        str: 摘要字符串，长度不超过 limit。
    """
    plain = content.replace("\n", " ").strip()
    return plain[:limit]


def split_tags(tags: str | None) -> List[str]:
    """将逗号分隔的标签字符串拆分为列表。

    Args:
        tags (str | None): 逗号分隔的标签字符串，如 "Python,FastAPI,后端"。

    Returns:
        List[str]: 标签列表，去除空白标签，如 ["Python", "FastAPI", "后端"]。
    """
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def resolve_author_name(user: User | None) -> str | None:
    """获取作者的展示名称（优先用户名，其次邮箱，最后手机号）。

    Args:
        user (User | None): 作者用户对象，可为 None（用户已删除时）。

    Returns:
        str | None: 展示名称，用户不存在时返回 None。
    """
    if not user:
        return None
    return user.username or user.email or user.phone


def mark_recommendation_clicked(db: Session, user_id: int, article_id: int) -> None:
    """将当前用户命中的推荐记录标记为已点击（用于 CTR 统计）。

    当用户点击进入文章详情页时调用，将该用户对该文章的所有未点击推荐记录
    标记为 is_clicked=True，用于推荐效果分析中的点击率计算。

    Args:
        db (Session): 数据库会话。
        user_id (int): 当前用户 ID。
        article_id (int): 被点击的文章 ID。
    """
    records = (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.article_id == article_id,
            Recommendation.is_clicked == False,  # 只更新未点击的记录
        )
        .all()
    )
    if not records:
        return
    for record in records:
        record.is_clicked = True
        db.add(record)
    db.commit()


@router.post("/article/publish")
def publish_article(
    payload: ArticlePublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布新文章。

    发布流程：
      1. 将 Markdown 正文转换为 HTML（用于前端渲染）
      2. 自动生成摘要（取正文前 120 字符）
      3. 保存文章到数据库
      4. 若状态为 published：
         a. 推送推荐记录给相关用户（push_new_article_recommendations）
         b. 通知关注该作者的粉丝（create_new_article_notifications）

    Args:
        payload (ArticlePublishRequest): 发布请求体，包含标题/正文/分类/标签/状态。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户（作者）。

    Returns:
        成功响应，data 包含：
          - article_id: 新文章 ID
          - pushed_user_count: 推送推荐的用户数
          - notified_follower_count: 通知的粉丝数
    """
    # 将 Markdown 转换为 HTML，供前端直接渲染
    html_content = markdown(payload.content)
    article = Article(
        author_id=current_user.id,
        title=payload.title,
        content=payload.content,        # 保存原始 Markdown
        html_content=html_content,      # 保存转换后的 HTML
        summary=build_summary(payload.content),  # 自动生成摘要
        category=payload.category,
        tags=payload.tags,
        status=payload.status,
        create_time=datetime.utcnow(),
        update_time=datetime.utcnow(),
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    pushed_user_count = 0
    notified_follower_count = 0
    # 只有发布状态（非草稿）才触发推荐推送和粉丝通知
    if article.status == "published":
        pushed_user_count = push_new_article_recommendations(db, article)
        notified_follower_count = create_new_article_notifications(db, current_user, article)

    return success_response(
        {
            "article_id": article.id,
            "pushed_user_count": pushed_user_count,
            "notified_follower_count": notified_follower_count,
        },
        message="发布成功",
    )


@router.put("/article/edit")
def edit_article(
    payload: ArticleEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑已有文章。

    权限规则：
      - 文章作者可以编辑自己的文章
      - 管理员可以编辑任意文章

    特殊逻辑：
      - 若文章从草稿变为已发布，触发推荐推送和粉丝通知

    Args:
        payload (ArticleEditRequest): 编辑请求体，包含 article_id 和新内容。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 为空对象。

    Raises:
        HTTPException(404): 文章不存在或已删除。
        HTTPException(403): 非作者且非管理员时抛出。
    """
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    # 权限校验：只有作者或管理员可以编辑
    if article.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    previous_status = article.status  # 记录修改前的状态，用于判断是否触发通知

    # 更新文章字段
    article.title = payload.title
    article.content = payload.content
    article.html_content = markdown(payload.content)    # 重新转换 HTML
    article.summary = build_summary(payload.content)    # 重新生成摘要
    article.category = payload.category
    article.tags = payload.tags
    article.status = payload.status
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()

    # 草稿 → 发布：触发推荐推送和粉丝通知
    if previous_status != "published" and article.status == "published":
        push_new_article_recommendations(db, article)
        create_new_article_notifications(db, article.author or current_user, article)

    return success_response({}, message="编辑成功")


@router.delete("/article/delete")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除文章（将 is_deleted 标记为 True，不物理删除）。

    软删除的好处：
      - 保留数据，便于审计和恢复
      - 关联的行为记录、评论等不受影响

    权限规则：
      - 文章作者可以删除自己的文章
      - 管理员可以删除任意文章

    Args:
        article_id (int): 要删除的文章 ID（Query 参数）。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 为空对象。

    Raises:
        HTTPException(404): 文章不存在或已删除。
        HTTPException(403): 非作者且非管理员时抛出。
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article or article.is_deleted:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    # 软删除：只修改标志位，不删除数据库记录
    article.is_deleted = True
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()
    return success_response({}, message="删除成功")


@router.get("/article/detail")
def get_article_detail(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """获取文章详情。

    访问控制：
      - 已发布文章：所有人可访问（包括匿名用户）
      - 草稿/被拒绝文章：只有作者和管理员可访问

    登录用户额外功能：
      - 自动将阅读量 +1
      - 返回当前用户对该文章的点赞/收藏/稍后阅读状态
      - 返回当前用户是否关注了该文章作者
      - 将命中的推荐记录标记为已点击（用于 CTR 统计）

    Args:
        article_id (int): 文章 ID（Query 参数）。
        db (Session): 数据库会话。
        current_user (User | None): 当前用户，未登录时为 None。

    Returns:
        成功响应，data 包含文章完整信息和用户交互状态。
    """
    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 非发布状态的文章，只有作者和管理员可以查看
    if article.status != "published" and not (
        current_user and (current_user.role == "admin" or current_user.id == article.author_id)
    ):
        raise HTTPException(status_code=403, detail="权限不足")

    # 阅读量 +1（每次访问详情页都计数，不去重）
    article.view_count += 1
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()

    # 初始化用户交互状态（未登录时均为 False）
    is_liked = False
    is_collected = False
    is_saved_for_later = False
    is_followed_author = False

    # 查询作者的粉丝数
    follower_count = (
        db.query(UserFollow)
        .filter(UserFollow.following_id == article.author_id)
        .count()
    )

    if current_user:
        # 标记推荐记录为已点击（用于 CTR 统计）
        mark_recommendation_clicked(db, current_user.id, article.id)

        # 查询当前用户是否已点赞该文章
        is_liked = (
            db.query(ArticleLike)
            .filter(
                ArticleLike.article_id == article.id,
                ArticleLike.user_id == current_user.id,
            )
            .first()
            is not None
        )
        # 查询当前用户是否已收藏该文章
        is_collected = (
            db.query(ArticleCollect)
            .filter(
                ArticleCollect.article_id == article.id,
                ArticleCollect.user_id == current_user.id,
            )
            .first()
            is not None
        )
        # 查询当前用户是否已将该文章加入稍后阅读
        is_saved_for_later = (
            db.query(ArticleReadLater)
            .filter(
                ArticleReadLater.article_id == article.id,
                ArticleReadLater.user_id == current_user.id,
            )
            .first()
            is not None
        )
        # 查询当前用户是否关注了文章作者（自己的文章不显示关注状态）
        if current_user.id != article.author_id:
            is_followed_author = (
                db.query(UserFollow)
                .filter(
                    UserFollow.follower_id == current_user.id,
                    UserFollow.following_id == article.author_id,
                )
                .first()
                is not None
            )

    data = {
        "article_id": article.id,
        "title": article.title,
        "content": article.content,         # 原始 Markdown 内容
        "html_content": article.html_content,  # 转换后的 HTML 内容
        "category": article.category,
        "status": article.status,
        "tags": split_tags(article.tags),   # 标签列表（已拆分）
        "author": {
            "user_id": article.author_id,
            "username": resolve_author_name(article.author),
            "follower_count": follower_count,
            "is_followed": is_followed_author,
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "comment_count": article.comment_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "update_time": article.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_liked": is_liked,               # 当前用户是否已点赞
        "is_collected": is_collected,       # 当前用户是否已收藏
        "is_saved_for_later": is_saved_for_later,  # 当前用户是否已加入稍后阅读
    }
    return success_response(data)


def _build_article_list_item(article: Article) -> dict:
    """将文章 ORM 对象转换为列表项字典（不含正文，减少数据传输量）。

    Args:
        article (Article): 文章 ORM 实例。

    Returns:
        dict: 文章列表项，包含 ID/标题/摘要/分类/标签/作者/统计数据/时间。
    """
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,         # 摘要（不含完整正文）
        "category": article.category,
        "tags": split_tags(article.tags),
        "author": {
            "user_id": article.author_id,
            "username": resolve_author_name(article.author),
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "comment_count": article.comment_count,
        "status": article.status,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/article/list")
def list_articles(
    page: int = 1,
    page_size: int = 10,
    category: str | None = None,
    tags: str | None = None,
    keyword: str | None = None,
    order: str | None = "latest",
    db: Session = Depends(get_db),
):
    """获取文章列表（公开接口，无需登录）。

    支持多维度筛选和排序：
      - category: 按分类筛选
      - tags: 按标签筛选（多标签 AND 关系）
      - keyword: 全文搜索（标题/正文/摘要 LIKE 匹配）
      - order: 排序方式，"latest"（最新）或 "hottest"（最热，按阅读量）

    Args:
        page (int): 页码，从 1 开始。
        page_size (int): 每页数量，默认 10。
        category (str | None): 分类筛选。
        tags (str | None): 标签筛选，逗号分隔。
        keyword (str | None): 搜索关键词。
        order (str | None): 排序方式，默认 "latest"。
        db (Session): 数据库会话。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
    """
    # 基础过滤：只返回已发布且未删除的文章
    query = db.query(Article).filter(
        Article.is_deleted == False, Article.status == "published"
    )

    # 分类筛选
    if category:
        query = query.filter(Article.category == category)

    # 标签筛选：多标签 AND 关系（每个标签都必须包含）
    if tags:
        tag_list = split_tags(tags)
        for tag in tag_list:
            query = query.filter(Article.tags.like(f"%{tag}%"))

    # 关键词搜索：标题、正文、摘要任一包含即可（OR 关系）
    if keyword:
        query = query.filter(
            (Article.title.like(f"%{keyword}%"))
            | (Article.content.like(f"%{keyword}%"))
            | (Article.summary.like(f"%{keyword}%"))
        )

    # 排序：最热按阅读量降序，默认按创建时间降序
    if order == "hottest":
        query = query.order_by(desc(Article.view_count))
    else:
        query = query.order_by(desc(Article.create_time))

    # 分页查询
    total = query.count()
    items = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = {
        "list": [_build_article_list_item(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/article/my-list")
def list_my_articles(
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的文章列表（含草稿，需要登录）。

    与公开列表接口的区别：
      - 只返回当前用户的文章
      - 包含草稿（draft）和被拒绝（rejected）状态的文章
      - 支持按状态筛选

    Args:
        page (int): 页码，从 1 开始。
        page_size (int): 每页数量，默认 10。
        status (str | None): 状态筛选，"draft"/"published"/"rejected"，不填返回全部。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
    """
    # 只查当前用户的文章，排除已软删除的
    query = db.query(Article).filter(
        Article.author_id == current_user.id, Article.is_deleted == False
    )
    # 可选按状态筛选
    if status:
        query = query.filter(Article.status == status)

    total = query.count()
    items = (
        query.order_by(desc(Article.create_time))  # 按创建时间降序
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = {
        "list": [_build_article_list_item(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)
