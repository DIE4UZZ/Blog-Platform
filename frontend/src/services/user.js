import { request } from "./http.js";

const USER_INFO_KEY = "blog_platform_user_info";

/**
 * 使用用户名和邮箱/手机号注册用户。
 * @param {{ username: string, email?: string, phone?: string, password: string }} payload 注册参数。
 * @returns {Promise<{ user_id?: number }>} 接口返回数据。
 */
export function registerUser(payload) {
  return request({
    url: "/user/register",
    method: "post",
    data: payload,
  });
}

/**
 * 使用用户名、邮箱或手机号登录并获取 Token。
 * @param {{ account?: string, email?: string, username?: string, phone?: string, password: string }} payload 登录参数。
 * @returns {Promise<{ token?: string, user_id?: number }>} 接口返回数据。
 */
export function loginUser(payload) {
  return request({
    url: "/user/login",
    method: "post",
    data: payload,
  });
}

/**
 * 获取当前登录用户信息。
 * @returns {Promise<Object>} 用户信息。
 */
export function fetchUserInfo() {
  return request({
    url: "/user/info",
    method: "get",
  });
}

/**
 * 更新用户偏好标签。
 * @param {{ preference_tags: string }} payload 偏好标签参数。
 * @returns {Promise<void>} 更新结果。
 */
export function updatePreferenceTags(payload) {
  return request({
    url: "/user/preference",
    method: "put",
    data: payload,
  });
}

export function getCachedUserInfo() {
  try {
    const raw = window.localStorage.getItem(USER_INFO_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;
  }
}

export function setCachedUserInfo(userInfo) {
  window.localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo || {}));
}

export function clearCachedUserInfo() {
  window.localStorage.removeItem(USER_INFO_KEY);
}

export async function refreshCurrentUserInfo() {
  const userInfo = await fetchUserInfo();
  setCachedUserInfo(userInfo);
  return userInfo;
}
