import { request } from "./http.js";

/**
 * 获取文章列表。
 * @param {{ page?: number, page_size?: number, category?: string, tags?: string, keyword?: string, order?: string }} params 查询参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 文章列表数据。
 */
export function fetchArticleList(params) {
  return request({
    url: "/article/list",
    method: "get",
    params,
  });
}

/**
 * 获取文章详情。
 * @param {number|string} articleId 文章 ID。
 * @returns {Promise<Object>} 文章详情数据。
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
 * 发布文章。
 * @param {{ title: string, content: string, category: string, tags?: string, status?: string }} payload 文章参数。
 * @returns {Promise<{ article_id?: number }>} 发布结果。
 */
export function publishArticle(payload) {
  return request({
    url: "/article/publish",
    method: "post",
    data: payload,
  });
}

/**
 * 编辑文章。
 * @param {{ article_id: number|string, title: string, content: string, category: string, tags?: string, status?: string }} payload 文章参数。
 * @returns {Promise<void>} 编辑结果。
 */
export function editArticle(payload) {
  return request({
    url: "/article/edit",
    method: "put",
    data: payload,
  });
}

/**
 * 获取当前用户文章列表。
 * @param {{ page?: number, page_size?: number, status?: string }} params 查询参数。
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
 * 删除文章。
 * @param {number|string} articleId 文章 ID。
 * @returns {Promise<void>} 删除结果。
 */
export function deleteArticle(articleId) {
  return request({
    url: "/article/delete",
    method: "delete",
    params: { article_id: articleId },
  });
}

/**
 * 切换文章点赞状态。
 * @param {{ article_id: number|string, action: string }} payload 点赞参数。
 * @returns {Promise<{ like_count?: number, is_liked?: boolean }>} 点赞结果。
 */
export function toggleLike(payload) {
  return request({
    url: "/article/like",
    method: "post",
    data: payload,
  });
}

/**
 * 切换文章收藏状态。
 * @param {{ article_id: number|string, action: string }} payload 收藏参数。
 * @returns {Promise<{ collect_count?: number, is_collected?: boolean }>} 收藏结果。
 */
export function toggleCollect(payload) {
  return request({
    url: "/article/collect",
    method: "post",
    data: payload,
  });
}
