/**
 * services/leaderboard.js —— 排行榜 API 封装模块
 *
 * 提供排行榜相关接口（均为公开接口，无需登录）：
 *   - fetchRankList        : 获取文章排行榜（按热度或最新排序）
 *   - fetchHotSearch       : 获取热搜关键词榜
 *   - fetchRecommendFollow : 获取推荐关注的创作者列表
 *
 * 热度分数公式（后端计算）：
 *   阅读量×1 + 点赞量×3 + 收藏量×5 + 评论量×4
 */

import { request } from "./http.js";

/**
 * 获取文章排行榜列表（公开接口）。
 *
 * 支持按分类筛选、关键词搜索和排序方式切换。
 *
 * @param {{ page?: number, page_size?: number, category?: string, keyword?: string, order?: string }} params - 查询参数。
 *   - category: 分类筛选（精确匹配）
 *   - keyword: 标题关键词搜索（模糊匹配）
 *   - order: "hottest"（热度降序，默认）或 "latest"（最新）
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 排行榜列表数据。
 *   list 中每项包含 article_id/title/summary/cover/hot_value/category/create_time。
 */
export function fetchRankList(params) {
  return request({
    url: "/rank/list",
    method: "get",
    params,
  });
}

/**
 * 获取热搜关键词榜（公开接口）。
 *
 * 统计用户搜索行为，按搜索次数降序排列。
 * 前 3 名的 is_hot 字段为 true（用于前端显示"热"标签）。
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 热搜列表数据。
 *   list 中每项包含 keyword/count/is_hot。
 */
export function fetchHotSearch(params) {
  return request({
    url: "/rank/hot-search",
    method: "get",
    params,
  });
}

/**
 * 获取推荐关注的创作者列表（公开接口，登录后可显示是否已关注）。
 *
 * 推荐策略：按总阅读量和文章数排序，返回 Top-N 创作者。
 * 登录用户会额外返回 followed 字段（是否已关注）。
 *
 * @param {{ limit?: number }} params - 查询参数。
 *   - limit: 返回数量（默认 6）
 * @returns {Promise<{ list: Array }>} 推荐创作者列表。
 *   list 中每项包含 user_id/name/desc/article_count/view_count/follower_count/followed。
 */
export function fetchRecommendFollow(params) {
  return request({
    url: "/rank/recommend",
    method: "get",
    params,
  });
}
