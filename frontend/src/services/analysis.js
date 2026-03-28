import { request } from "./http.js";

/**
 * Fetch read trend analytics.
 * @param {{ user_id?: number, start_date?: string, end_date?: string, granularity?: string }} params Query parameters.
 * @returns {Promise<Object>} Read trend payload.
 */
export function fetchReadTrend(params) {
  return request({
    url: "/analysis/read-trend",
    method: "get",
    params,
  });
}

/**
 * Fetch recommend effect analytics.
 * @param {{ user_id?: number, start_date?: string, end_date?: string }} params Query parameters.
 * @returns {Promise<Object>} Recommend effect payload.
 */
export function fetchRecommendEffect(params) {
  return request({
    url: "/analysis/recommend-effect",
    method: "get",
    params,
  });
}

/**
 * Fetch user portrait analytics.
 * @param {{ user_id?: number }} params Query parameters.
 * @returns {Promise<Object>} User portrait payload.
 */
export function fetchUserPortrait(params) {
  return request({
    url: "/analysis/user-portrait",
    method: "get",
    params,
  });
}

/**
 * Fetch user active heatmap analytics.
 * @param {{ user_id?: number, days?: number }} params Query parameters.
 * @returns {Promise<Object>} Active heatmap payload.
 */
export function fetchActiveHeatmap(params) {
  return request({
    url: "/analysis/active-heatmap",
    method: "get",
    params,
  });
}

/**
 * Fetch content performance analytics.
 * @param {{ user_id?: number, limit?: number }} params Query parameters.
 * @returns {Promise<Object>} Content performance payload.
 */
export function fetchContentPerformance(params) {
  return request({
    url: "/analysis/content-performance",
    method: "get",
    params,
  });
}
