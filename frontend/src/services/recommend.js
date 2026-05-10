/**
 * services/recommend.js —— 推荐系统 API 封装模块
 *
 * 提供个性化推荐相关接口：
 *   - fetchRecommendList    : 获取首页个性化推荐文章列表
 *   - fetchSimilarArticles  : 获取与指定文章相似的文章列表
 *
 * 推荐算法说明（后端实现）：
 *   - 登录用户：基于用户偏好标签 + 历史行为（阅读/点赞/收藏）的协同过滤推荐
 *   - 未登录用户：基于文章热度的通用推荐（降级策略）
 *   - 相似文章：基于 TF-IDF 关键词提取的内容相似度计算
 */

import { request } from "./http.js";

/**
 * 获取首页个性化推荐文章列表。
 *
 * 推荐逻辑（后端）：
 *   1. 已登录：根据用户偏好标签和历史行为计算推荐分数
 *   2. 未登录：返回热度最高的文章（降级策略）
 *   3. 过滤已读文章（避免重复推荐）
 *
 * @param {{ page?: number, page_size?: number }} params - 分页参数。
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} 推荐文章列表。
 */
export function fetchRecommendList(params) {
  return request({
    url: "/recommend/list",
    method: "get",
    params,
  });
}

/**
 * 获取与指定文章相似的文章列表（文章详情页"相关推荐"使用）。
 *
 * 相似度计算（后端）：
 *   - 基于 TF-IDF 算法提取文章关键词
 *   - 计算关键词向量的余弦相似度
 *   - 返回相似度最高的 size 篇文章
 *
 * @param {{ article_id: number|string, size?: number }} params - 查询参数。
 *   - article_id: 基准文章 ID（必填）
 *   - size: 返回数量（默认 5）
 * @returns {Promise<{ list: Array }>} 相似文章列表。
 */
export function fetchSimilarArticles(params) {
  return request({
    url: "/recommend/similar",
    method: "get",
    params,
  });
}
