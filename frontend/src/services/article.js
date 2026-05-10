/**
 * services/article.js —— 文章相关 API 封装模块
 *
 * 提供文章的增删改查、点赞、收藏等接口调用：
 *   - fetchArticleList   : 获取文章列表（支持分类/标签/关键词/排序筛选）
 *   - fetchArticleDetail : 获取文章详情（含正文内容）
 *   - publishArticle     : 发布新文章
 *   - editArticle        : 编辑已有文章
 *   - fetchMyArticles    : 获取当前用户的文章列表
 *   - deleteArticle      : 删除文章（软删除）
 *   - toggleLike         : 点赞/取消点赞
 *   - toggleCollect      : 收藏/取消收藏
 *
 * 所有接口均通过 http.js 的 request 函数发起，自动携带 JWT Token。
 */

import { request } from "./http.js";

/**
 * 获取文章列表（公开接口，无需登录）。
 *
 * 支持多维度筛选和排序：
 *   - category: 分类精确匹配
 *   - tags: 标签模糊匹配
 *   - keyword: 标题/摘要关键词搜索
 *   - order: "latest"（最新）或 "hottest"（热度）
 *
 * @param {{ page?: number, page_size?: number, category?: string, tags?: string, keyword?: string, order?: string }} params - 查询参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 文章列表数据。
 */
export function fetchArticleList(params) {
  return request({
    url: "/article/list",
    method: "get",
    params,   // 作为 URL Query 参数传递
  });
}

/**
 * 获取文章详情（公开接口，无需登录）。
 *
 * 返回完整文章内容，包括正文（Markdown 格式）、作者信息、
 * 统计数据（阅读量/点赞数/收藏数/评论数）以及当前用户的互动状态。
 * 调用此接口会自动增加文章阅读量。
 *
 * @param {number|string} articleId - 文章 ID。
 * @returns {Promise<Object>} 文章详情数据（含 is_liked/is_collected 等状态字段）。
 */
export function fetchArticleDetail(articleId) {
  return request({
    url: "/article/detail",
    method: "get",
    params: {
      article_id: articleId,
    },
  });
}

/**
 * 发布新文章（需要登录）。
 *
 * status 字段控制发布状态：
 *   - "published"：直接发布（需管理员审核后才公开，或直接公开，取决于系统配置）
 *   - "draft"：保存为草稿
 *
 * @param {{ title: string, content: string, category: string, tags?: string, status?: string }} payload - 文章参数。
 *   - title: 文章标题（必填）
 *   - content: 文章正文（Markdown 格式，必填）
 *   - category: 文章分类（必填）
 *   - tags: 标签（逗号分隔字符串，可选）
 *   - status: 发布状态（默认 "published"）
 * @returns {Promise<{ article_id?: number }>} 发布成功后返回新文章 ID。
 */
export function publishArticle(payload) {
  return request({
    url: "/article/publish",
    method: "post",
    data: payload,
  });
}

/**
 * 编辑已有文章（需要登录，且只能编辑自己的文章）。
 *
 * @param {{ article_id: number|string, title: string, content: string, category: string, tags?: string, status?: string }} payload - 文章参数。
 *   - article_id: 要编辑的文章 ID（必填）
 *   - 其他字段同 publishArticle
 * @returns {Promise<void>} 编辑成功时 resolve。
 */
export function editArticle(payload) {
  return request({
    url: "/article/edit",
    method: "put",
    data: payload,
  });
}

/**
 * 获取当前登录用户的文章列表（需要登录）。
 *
 * 与 fetchArticleList 不同，此接口返回当前用户的所有文章（包括草稿和已驳回的）。
 *
 * @param {{ page?: number, page_size?: number, status?: string }} params - 查询参数。
 *   - status: 状态筛选（"draft"/"published"/"rejected"），不传则返回所有状态
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 我的文章列表。
 */
export function fetchMyArticles(params) {
  return request({
    url: "/article/my-list",
    method: "get",
    params,
  });
}

/**
 * 删除文章（软删除，需要登录，且只能删除自己的文章）。
 *
 * 软删除：文章不会从数据库中物理删除，而是标记 is_deleted=True，
 * 前端和普通用户接口不再返回该文章，但管理员仍可查看。
 *
 * @param {number|string} articleId - 要删除的文章 ID。
 * @returns {Promise<void>} 删除成功时 resolve。
 */
export function deleteArticle(articleId) {
  return request({
    url: "/article/delete",
    method: "delete",
    params: { article_id: articleId },
  });
}

/**
 * 切换文章点赞状态（需要登录）。
 *
 * 幂等设计：重复点赞不会报错，重复取消也不会报错。
 *
 * @param {{ article_id: number|string, action: string }} payload - 点赞参数。
 *   - article_id: 文章 ID
 *   - action: "like"（点赞）或 "unlike"（取消点赞）
 * @returns {Promise<{ like_count?: number, is_liked?: boolean }>} 操作后的点赞数和状态。
 */
export function toggleLike(payload) {
  return request({
    url: "/article/like",
    method: "post",
    data: payload,
  });
}

/**
 * 切换文章收藏状态（需要登录）。
 *
 * 幂等设计：重复收藏不会报错，重复取消也不会报错。
 * 收藏的文章会出现在用户的"内容库 → 收藏"列表中。
 *
 * @param {{ article_id: number|string, action: string }} payload - 收藏参数。
 *   - article_id: 文章 ID
 *   - action: "collect"（收藏）或 "uncollect"（取消收藏）
 * @returns {Promise<{ collect_count?: number, is_collected?: boolean }>} 操作后的收藏数和状态。
 */
export function toggleCollect(payload) {
  return request({
    url: "/article/collect",
    method: "post",
    data: payload,
  });
}
