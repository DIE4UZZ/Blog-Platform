import { request } from "./http.js";

/**
 * 获取文章评论列表。
 * @param {{ article_id: number|string, page?: number, page_size?: number }} params 查询参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 评论列表数据。
 */
export function fetchCommentList(params) {
  return request({
    url: "/comment/list",
    method: "get",
    params,
  });
}

/**
 * 提交评论或回复。
 * @param {{ article_id: number|string, content: string, parent_id?: number }} payload 评论参数。
 * @returns {Promise<{ comment_id?: number }>} 提交结果。
 */
export function submitComment(payload) {
  return request({
    url: "/behavior/comment",
    method: "post",
    data: payload,
  });
}
