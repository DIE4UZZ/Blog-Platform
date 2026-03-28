import { request } from "./http.js";

/**
 * Fetch homepage recommend list.
 * @param {{ page?: number, page_size?: number }} params Query parameters.
 * @returns {Promise<{ list: Array, total: number, page: number, page_size: number }>} Recommend list payload.
 */
export function fetchRecommendList(params) {
  return request({
    url: "/recommend/list",
    method: "get",
    params,
  });
}

/**
 * Fetch similar articles for a given article.
 * @param {{ article_id: number|string, size?: number }} params Query parameters.
 * @returns {Promise<{ list: Array }>} Similar list payload.
 */
export function fetchSimilarArticles(params) {
  return request({
    url: "/recommend/similar",
    method: "get",
    params,
  });
}
