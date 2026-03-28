import { request } from "./http.js";

/**
 * Fetch leaderboard list.
 * @param {{ page?: number, page_size?: number, category?: string, keyword?: string, order?: string }} params Query params.
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} Leaderboard list payload.
 */
export function fetchRankList(params) {
  return request({
    url: "/rank/list",
    method: "get",
    params,
  });
}

/**
 * Fetch hot search keywords.
 * @param {{ page?: number, page_size?: number }} params Query params.
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} Hot search payload.
 */
export function fetchHotSearch(params) {
  return request({
    url: "/rank/hot-search",
    method: "get",
    params,
  });
}

/**
 * Fetch recommended creators list.
 * @param {{ limit?: number }} params Query params.
 * @returns {Promise<{ list: Array }>} Recommended creators payload.
 */
export function fetchRecommendFollow(params) {
  return request({
    url: "/rank/recommend",
    method: "get",
    params,
  });
}
