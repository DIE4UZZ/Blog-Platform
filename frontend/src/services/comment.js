/**
 * services/comment.js —— 评论相关 API 封装模块
 *
 * 提供文章评论的查询和提交功能：
 *   - fetchCommentList : 获取文章评论列表（支持分页，含嵌套回复）
 *   - submitComment    : 提交评论或回复（需要登录）
 *
 * 评论结构说明：
 *   - 顶级评论：parent_id 为 null
 *   - 回复评论：parent_id 为被回复的评论 ID
 *   - 后端返回的评论列表已按树形结构组织（顶级评论含 replies 子列表）
 */

import { request } from "./http.js";

/**
 * 获取文章评论列表（公开接口，无需登录）。
 *
 * 返回的评论列表按树形结构组织：
 *   - 顶级评论按时间排序
 *   - 每条顶级评论包含 replies 字段（子评论列表）
 *
 * @param {{ article_id: number|string, page?: number, page_size?: number }} params - 查询参数。
 *   - article_id: 文章 ID（必填）
 *   - page: 页码，从 1 开始（默认 1）
 *   - page_size: 每页数量（默认 10）
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 评论列表数据。
 */
export function fetchCommentList(params) {
  return request({
    url: "/comment/list",
    method: "get",
    params,   // 作为 URL Query 参数传递
  });
}

/**
 * 提交评论或回复（需要登录）。
 *
 * 提交后后端会：
 *   1. 创建评论记录
 *   2. 更新文章评论数统计
 *   3. 发送通知给文章作者（新评论通知）
 *   4. 若是回复，发送通知给被回复的评论作者（回复通知）
 *
 * @param {{ article_id: number|string, content: string, parent_id?: number }} payload - 评论参数。
 *   - article_id: 被评论的文章 ID（必填）
 *   - content: 评论内容（必填）
 *   - parent_id: 父评论 ID（回复时必填，顶级评论时不传）
 * @returns {Promise<{ comment_id?: number }>} 提交成功后返回新评论 ID。
 */
export function submitComment(payload) {
  return request({
    url: "/behavior/comment",
    method: "post",
    data: payload,
  });
}
