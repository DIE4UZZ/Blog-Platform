/**
 * services/library.js —— 用户内容库 API 封装模块
 *
 * 提供用户个人内容库的查询和管理接口（均需要登录）：
 *   - fetchCollections : 获取收藏文章列表
 *   - fetchReadHistory : 获取阅读历史（按文章去重，保留最近阅读时间）
 *   - fetchReadLater   : 获取稍后阅读列表
 *   - toggleReadLater  : 添加/移除稍后阅读
 *
 * 内容库三大功能：
 *   1. 收藏夹：用户主动收藏的文章（通过 article.js 的 toggleCollect 操作）
 *   2. 阅读历史：系统自动记录的阅读行为（通过 behavior.js 的 trackRead 上报）
 *   3. 稍后阅读：用户标记"稍后阅读"的文章（通过本模块的 toggleReadLater 操作）
 */

import { request } from "./http.js";

/**
 * 获取当前用户的收藏文章列表（需要登录）。
 *
 * 按收藏时间降序排列，过滤已删除或未发布的文章。
 * 返回数据中每项额外包含 collected_at（收藏时间）字段。
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 收藏列表数据。
 */
export function fetchCollections(params) {
  return request({
    url: "/library/collections",
    method: "get",
    params,
  });
}

/**
 * 获取当前用户的阅读历史（需要登录）。
 *
 * 特点：
 *   - 按文章去重（同一篇文章多次阅读合并为一条）
 *   - 保留最近阅读时间、累计阅读次数、最长阅读时长、最大滚动深度
 *   - 按最近阅读时间降序排列
 *
 * 返回数据中每项额外包含：
 *   - last_read_time: 最近阅读时间
 *   - read_count: 累计阅读次数
 *   - last_read_duration: 最近一次阅读时长（秒）
 *   - max_scroll_depth: 历史最大滚动深度（0~1）
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 阅读历史数据。
 */
export function fetchReadHistory(params) {
  return request({
    url: "/library/history",
    method: "get",
    params,
  });
}

/**
 * 获取当前用户的稍后阅读列表（需要登录）。
 *
 * 按添加时间降序排列，过滤已删除或未发布的文章。
 * 返回数据中每项额外包含 saved_at（添加时间）字段。
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 稍后阅读列表数据。
 */
export function fetchReadLater(params) {
  return request({
    url: "/library/read-later",
    method: "get",
    params,
  });
}

/**
 * 添加或移除稍后阅读（需要登录）。
 *
 * 幂等设计：重复添加/移除不会报错。
 *
 * @param {{ article_id: number|string, action: string }} payload - 操作参数。
 *   - article_id: 文章 ID
 *   - action: "save"（添加到稍后阅读）或 "remove"（从稍后阅读移除）
 * @returns {Promise<{ article_id: number, is_saved_for_later: boolean, read_later_count: number }>} 操作结果。
 */
export function toggleReadLater(payload) {
  return request({
    url: "/library/read-later",
    method: "post",
    data: payload,
  });
}
