/**
 * services/analysis.js —— 数据分析 API 封装模块
 *
 * 提供用户行为数据分析相关接口（均需要登录）：
 *   - fetchReadTrend          : 阅读趋势分析（按时间维度统计阅读量）
 *   - fetchRecommendEffect    : 推荐效果分析（推荐点击率、转化率等）
 *   - fetchUserPortrait       : 用户画像分析（兴趣标签、行为偏好等）
 *   - fetchActiveHeatmap      : 用户活跃热力图（按时间分布的活跃度）
 *   - fetchContentPerformance : 内容表现分析（文章阅读量、互动率等）
 *
 * 数据来源：后端从 user_behavior 表聚合计算，数据有一定延迟。
 * 分析维度：支持按用户 ID、时间范围、粒度（日/周/月）等筛选。
 */

import { request } from "./http.js";

/**
 * 获取阅读趋势分析数据（需要登录）。
 *
 * 按时间维度统计用户的阅读量变化趋势，用于折线图展示。
 * 支持按日/周/月粒度聚合，以及自定义时间范围筛选。
 *
 * @param {{ user_id?: number, start_date?: string, end_date?: string, granularity?: string }} params - 查询参数。
 *   - user_id: 用户 ID（管理员可查看其他用户，普通用户只能查自己）
 *   - start_date: 开始日期（格式 "YYYY-MM-DD"）
 *   - end_date: 结束日期（格式 "YYYY-MM-DD"）
 *   - granularity: 时间粒度（"day"/"week"/"month"，默认 "day"）
 * @returns {Promise<Object>} 阅读趋势数据（含时间序列和统计指标）。
 */
export function fetchReadTrend(params) {
  return request({
    url: "/analysis/read-trend",
    method: "get",
    params,
  });
}

/**
 * 获取推荐效果分析数据（需要登录）。
 *
 * 分析推荐系统的效果指标：
 *   - 推荐文章的点击率（CTR）
 *   - 推荐文章的阅读完成率
 *   - 推荐文章的互动率（点赞/收藏/评论）
 *
 * @param {{ user_id?: number, start_date?: string, end_date?: string }} params - 查询参数。
 * @returns {Promise<Object>} 推荐效果数据（含各项效果指标）。
 */
export function fetchRecommendEffect(params) {
  return request({
    url: "/analysis/recommend-effect",
    method: "get",
    params,
  });
}

/**
 * 获取用户画像分析数据（需要登录）。
 *
 * 基于用户历史行为（阅读/点赞/收藏/搜索）分析用户兴趣偏好：
 *   - 兴趣标签分布（词云/饼图）
 *   - 阅读时长分布
 *   - 活跃时间段分布
 *   - 内容偏好（分类/标签）
 *
 * @param {{ user_id?: number }} params - 查询参数。
 * @returns {Promise<Object>} 用户画像数据（含兴趣标签、行为偏好等）。
 */
export function fetchUserPortrait(params) {
  return request({
    url: "/analysis/user-portrait",
    method: "get",
    params,
  });
}

/**
 * 获取用户活跃热力图数据（需要登录）。
 *
 * 统计用户在过去 N 天内每天的活跃行为次数，
 * 用于类似 GitHub 贡献图的热力图展示。
 *
 * @param {{ user_id?: number, days?: number }} params - 查询参数。
 *   - days: 统计天数（默认 90 天）
 * @returns {Promise<Object>} 活跃热力图数据（含日期和活跃度数组）。
 */
export function fetchActiveHeatmap(params) {
  return request({
    url: "/analysis/active-heatmap",
    method: "get",
    params,
  });
}

/**
 * 获取内容表现分析数据（需要登录）。
 *
 * 分析当前用户发布的文章的表现指标：
 *   - 各文章的阅读量、点赞数、收藏数、评论数
 *   - 文章互动率（互动次数/阅读量）
 *   - Top-N 表现最好的文章
 *
 * @param {{ user_id?: number, limit?: number }} params - 查询参数。
 *   - limit: 返回文章数量（默认 10）
 * @returns {Promise<Object>} 内容表现数据（含文章列表和统计指标）。
 */
export function fetchContentPerformance(params) {
  return request({
    url: "/analysis/content-performance",
    method: "get",
    params,
  });
}
