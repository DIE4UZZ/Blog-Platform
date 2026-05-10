/**
 * services/social.js —— 社交功能 API 封装模块
 *
 * 提供用户关注、通知、关注动态等社交功能接口：
 *   - toggleFollow         : 关注/取消关注用户
 *   - fetchFollowingFeed   : 获取关注用户的最新文章动态
 *   - fetchNotifications   : 获取通知列表
 *   - markNotificationsRead: 标记通知为已读
 *   - fetchFollowList      : 获取关注列表或粉丝列表
 *
 * 所有接口均需要登录（JWT Token），通过 http.js 自动附加认证头。
 */

import { request } from "./http.js";

/**
 * 关注或取消关注用户（需要登录）。
 *
 * 幂等设计：重复关注/取消不会报错。
 * 关注成功后，被关注者会收到"新关注者"通知。
 *
 * @param {{ target_user_id: number, action: string }} payload - 关注参数。
 *   - target_user_id: 目标用户 ID（不能是自己）
 *   - action: "follow"（关注）或 "unfollow"（取消关注）
 * @returns {Promise<{ target_user_id: number, is_followed: boolean, follower_count: number, following_count: number }>} 操作结果。
 */
export function toggleFollow(payload) {
  return request({
    url: "/follow/action",
    method: "post",
    data: payload,
  });
}

/**
 * 获取关注用户的最新文章动态（关注动态流，需要登录）。
 *
 * 只返回当前用户关注的作者发布的已发布文章，按发布时间降序排列。
 * 若未关注任何人，返回空列表。
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 动态列表数据。
 */
export function fetchFollowingFeed(params) {
  return request({
    url: "/feed/following",
    method: "get",
    params,
  });
}

/**
 * 获取当前用户的通知列表（需要登录）。
 *
 * 通知类型：
 *   - new_article  : 关注的作者发布了新文章
 *   - new_comment  : 自己的文章收到了新评论
 *   - comment_reply: 自己的评论收到了回复
 *   - new_follower : 有新用户关注了自己
 *
 * @param {{ page?: number, page_size?: number, unread_only?: boolean }} params - 查询参数。
 *   - unread_only: true 时只返回未读通知
 * @returns {Promise<{ list: Array, total: number, unread_count: number }>} 通知列表数据（含未读总数）。
 */
export function fetchNotifications(params) {
  return request({
    url: "/notification/list",
    method: "get",
    params,
  });
}

/**
 * 标记通知为已读（需要登录）。
 *
 * 支持两种模式：
 *   - read_all=true：标记所有未读通知为已读（一键已读）
 *   - read_all=false：标记指定 ID 列表的通知为已读
 *
 * @param {{ read_all: boolean, notification_ids?: number[] }} payload - 请求参数。
 * @returns {Promise<{ updated_count: number, unread_count: number }>} 更新数量和剩余未读数。
 */
export function markNotificationsRead(payload) {
  return request({
    url: "/notification/read",
    method: "put",
    data: payload,
  });
}

/**
 * 获取当前用户的关注列表或粉丝列表（需要登录）。
 *
 * @param {{ list_type?: string, page?: number, page_size?: number }} params - 查询参数。
 *   - list_type: "following"（我关注的人，默认）或 "followers"（关注我的人）
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 用户列表数据。
 */
export function fetchFollowList(params) {
  return request({
    url: "/follow/list",
    method: "get",
    params,
  });
}
