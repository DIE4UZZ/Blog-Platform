/**
 * services/admin.js —— 管理员后台 API 封装模块
 *
 * 提供管理员专用的用户管理、文章审核、异常内容检测接口：
 *   - fetchAdminUsers      : 获取用户列表（支持关键词/角色筛选）
 *   - updateAdminUserRole  : 修改用户角色（user/admin）
 *   - fetchAdminArticles   : 获取文章列表（支持状态/关键词筛选）
 *   - reviewAdminArticle   : 文章审核（发布/驳回/退回草稿）
 *   - fetchAbnormalContent : 获取异常内容检测结果（关键词命中）
 *
 * 权限说明：
 *   - 所有接口均需要管理员角色（role="admin"）
 *   - 路由守卫（router/index.js）会在前端拦截非管理员访问
 *   - 后端通过 require_admin 依赖进行二次校验（双重保护）
 */

import { request } from "./http.js";

/**
 * 获取用户列表（管理员专用）。
 *
 * 支持按角色筛选和关键词搜索（用户名/邮箱/手机号模糊匹配）。
 *
 * @param {{ page?: number, page_size?: number, keyword?: string, role?: string }} params - 查询参数。
 *   - keyword: 搜索关键词（模糊匹配用户名/邮箱/手机号）
 *   - role: 角色筛选（"user" 或 "admin"）
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 用户列表数据。
 */
export function fetchAdminUsers(params) {
  return request({
    url: "/admin/users",
    method: "get",
    params,
  });
}

/**
 * 修改用户角色（管理员专用）。
 *
 * 安全限制：管理员不能取消自己的管理员权限。
 *
 * @param {{ user_id: number, role: string }} payload - 请求参数。
 *   - user_id: 目标用户 ID
 *   - role: 新角色（"user" 或 "admin"）
 * @returns {Promise<void>} 更新成功时 resolve。
 */
export function updateAdminUserRole(payload) {
  return request({
    url: "/admin/user/role",
    method: "put",
    data: payload,
  });
}

/**
 * 获取文章列表（管理员专用，包含所有状态的文章）。
 *
 * 与普通文章列表不同，管理员可以查看所有状态（草稿/已发布/已驳回）的文章。
 *
 * @param {{ page?: number, page_size?: number, status?: string, keyword?: string }} params - 查询参数。
 *   - status: 状态筛选（"draft"/"published"/"rejected"）
 *   - keyword: 搜索关键词（模糊匹配标题/摘要/正文）
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 文章列表数据。
 */
export function fetchAdminArticles(params) {
  return request({
    url: "/admin/articles",
    method: "get",
    params,
  });
}

/**
 * 审核文章（管理员专用）。
 *
 * 支持三种审核结果：
 *   - "published"：通过审核，文章公开发布
 *   - "draft"：退回草稿，作者可继续修改
 *   - "rejected"：驳回，文章不予发布
 *
 * @param {{ article_id: number, status: string }} payload - 审核参数。
 * @returns {Promise<void>} 审核成功时 resolve。
 */
export function reviewAdminArticle(payload) {
  return request({
    url: "/admin/article/review",
    method: "put",
    data: payload,
  });
}

/**
 * 获取异常内容检测结果（管理员专用）。
 *
 * 后端使用关键词黑名单对文章和评论进行扫描，
 * 返回命中关键词的内容列表，供管理员人工审核。
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 异常内容列表。
 *   list 中每项包含 type（article/comment）/target_id/snippet/hit_keywords/time。
 */
export function fetchAbnormalContent(params) {
  return request({
    url: "/admin/content/abnormal",
    method: "get",
    params,
  });
}
