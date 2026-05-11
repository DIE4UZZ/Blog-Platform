/**
 * services/user.js —— 用户相关 API 封装模块
 *
 * 提供用户注册、登录、信息获取与缓存管理等功能：
 *   - registerUser     : 用户注册
 *   - loginUser        : 用户登录（获取 JWT Token）
 *   - fetchUserInfo    : 获取当前登录用户信息（需要 Token）
 *   - updatePreferenceTags : 更新用户偏好标签（用于个性化推荐）
 *   - getCachedUserInfo    : 从 localStorage 读取缓存的用户信息
 *   - setCachedUserInfo    : 将用户信息写入 localStorage 并触发更新事件
 *   - clearCachedUserInfo  : 清除 localStorage 中的用户信息
 *   - refreshCurrentUserInfo : 从服务端刷新用户信息并更新缓存
 *
 * 用户信息缓存说明：
 *   - 存储在 localStorage 的 "blog_platform_user_info" key 中
 *   - 更新/清除时会触发 "blog-user-info-updated" 自定义事件
 *   - 其他组件可监听该事件来响应用户信息变化（如导航栏头像更新）
 */

import { request } from "./http.js";

// localStorage 中存储用户信息的 key 名
const USER_INFO_KEY = "blog_platform_user_info";

/**
 * 用户注册。
 *
 * @param {{ username: string, email?: string, phone?: string, password: string }} payload - 注册参数。
 *   - username: 用户名（必填）
 *   - email: 邮箱（与 phone 至少填一个）
 *   - phone: 手机号（与 email 至少填一个）
 *   - password: 密码（明文，后端会进行哈希处理）
 * @returns {Promise<{ user_id?: number }>} 注册成功后返回新用户 ID。
 */
export function registerUser(payload) {
  return request({
    url: "/user/register",
    method: "post",
    data: payload,
  });
}

/**
 * 用户登录，获取 JWT Token。
 *
 * 支持多种登录方式（用户名/邮箱/手机号 + 密码）。
 * 登录成功后需调用 setAuthToken 保存 Token，调用 setCachedUserInfo 缓存用户信息。
 *
 * @param {{ account?: string, email?: string, username?: string, phone?: string, password: string }} payload - 登录参数。
 * @returns {Promise<{ token?: string, user_id?: number }>} 登录成功后返回 Token 和用户 ID。
 */
export function loginUser(payload) {
  return request({
    url: "/user/login",
    method: "post",
    data: payload,
  });
}

/**
 * 获取当前登录用户的详细信息（需要 JWT Token）。
 *
 * 返回数据包含：user_id/username/email/phone/role/preference_tags 等。
 * 通常在登录后或页面刷新时调用，结果缓存到 localStorage。
 *
 * @returns {Promise<Object>} 当前用户信息对象。
 */
export function fetchUserInfo() {
  return request({
    url: "/user/info",
    method: "get",
  });
}

/**
 * 更新当前用户的偏好标签（用于个性化推荐算法）。
 *
 * 偏好标签格式：逗号分隔的字符串，如 "技术,前端,Vue"。
 * 更新后推荐系统会根据新标签调整推荐内容。
 *
 * @param {{ preference_tags: string }} payload - 偏好标签参数。
 * @returns {Promise<void>} 更新成功时 resolve，失败时 reject。
 */
export function updatePreferenceTags(payload) {
  return request({
    url: "/user/preference",
    method: "put",
    data: payload,
  });
}

/**
 * 更新当前用户的个人资料（用户名、邮箱、手机号、简介）。
 *
 * @param {{ username?: string, email?: string, phone?: string, bio?: string }} payload - 要更新的字段。
 * @returns {Promise<Object>} 更新后的用户信息。
 */
export function updateUserProfile(payload) {
  return request({
    url: "/user/profile",
    method: "put",
    data: payload,
  });
}

/**
 * 从 localStorage 读取缓存的用户信息（同步操作，无需网络请求）。
 *
 * 用于路由守卫、导航栏等需要快速获取用户信息的场景。
 * 若缓存不存在或 JSON 解析失败，返回 null。
 *
 * @returns {Object|null} 缓存的用户信息，未登录或解析失败时返回 null。
 */
export function getCachedUserInfo() {
  try {
    const raw = window.localStorage.getItem(USER_INFO_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;  // JSON 解析失败时静默返回 null
  }
}

/**
 * 将用户信息写入 localStorage 缓存，并触发全局更新事件。
 *
 * 触发 "blog-user-info-updated" 自定义事件，导航栏等组件可监听此事件
 * 来实时更新显示的用户名、头像等信息。
 *
 * @param {Object|null} userInfo - 要缓存的用户信息对象，传 null 时存储空对象。
 */
export function setCachedUserInfo(userInfo) {
  window.localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo || {}));
  // 触发自定义事件，通知其他组件用户信息已更新
  window.dispatchEvent(new CustomEvent("blog-user-info-updated"));
}

/**
 * 清除 localStorage 中的用户信息缓存，并触发全局更新事件。
 *
 * 通常在退出登录时调用（配合 clearAuthToken 一起使用）。
 * 触发 "blog-user-info-updated" 事件，导航栏等组件会响应并清空用户状态。
 */
export function clearCachedUserInfo() {
  window.localStorage.removeItem(USER_INFO_KEY);
  // 触发自定义事件，通知其他组件用户已退出
  window.dispatchEvent(new CustomEvent("blog-user-info-updated"));
}

/**
 * 从服务端刷新当前用户信息并更新本地缓存。
 *
 * 适用场景：
 *   - 用户修改个人信息后刷新缓存
 *   - 页面刷新后重新同步用户状态
 *   - Token 有效但缓存过期时重新获取
 *
 * @returns {Promise<Object>} 最新的用户信息对象。
 */
export async function refreshCurrentUserInfo() {
  const userInfo = await fetchUserInfo();   // 从服务端获取最新用户信息
  setCachedUserInfo(userInfo);              // 更新本地缓存并触发更新事件
  return userInfo;
}
