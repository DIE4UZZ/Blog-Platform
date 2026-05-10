/**
 * services/http.js —— HTTP 请求封装模块
 *
 * 基于 axios 封装统一的 HTTP 客户端，提供：
 *   1. Token 的本地存储管理（localStorage）
 *   2. 请求拦截器：自动附加 Authorization 请求头
 *   3. 响应拦截器：统一处理业务错误码和 Token 失效跳转
 *
 * 业务错误码约定：
 *   - code=0：请求成功，返回 payload.data
 *   - code=4002：Token 失效/未登录，自动清除本地凭证并跳转到登录页
 *   - 其他非 0：请求失败，弹出错误提示并 reject
 */

import axios from "axios";
import { ElMessage } from "element-plus";

// localStorage 中存储 Token 和用户信息的 key 名
const TOKEN_KEY = "blog_platform_token";
const USER_INFO_KEY = "blog_platform_user_info";

/**
 * 从 localStorage 读取 JWT Token。
 * @returns {string|null} Token 字符串，未登录时返回 null。
 */
export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

/**
 * 将 JWT Token 写入 localStorage（登录成功后调用）。
 * @param {string} token - 服务端返回的 JWT Token。
 */
export function setAuthToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

/**
 * 清除 localStorage 中的 JWT Token（退出登录时调用）。
 */
export function clearAuthToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

/**
 * 创建并配置 axios 实例。
 *
 * 配置项：
 *   - baseURL: "/api"（由 Vite 代理转发到后端 8000 端口）
 *   - timeout: 12000ms（12 秒超时）
 *   - 请求拦截器：自动附加 Bearer Token
 *   - 响应拦截器：统一处理业务错误码
 *
 * @returns {import("axios").AxiosInstance} 配置好的 axios 实例。
 */
function createHttpClient() {
  const client = axios.create({
    baseURL: "/api",          // 所有请求前缀 /api，由 vite.config.js 代理到后端
    timeout: 12000,           // 请求超时时间：12 秒
    headers: {
      "Content-Type": "application/json",
    },
  });
  // 注册请求拦截器和响应拦截器
  client.interceptors.request.use(attachAuthHeader, handleRequestError);
  client.interceptors.response.use(normalizeResponse, handleResponseError);
  return client;
}

// 全局唯一的 HTTP 客户端实例
const httpClient = createHttpClient();

/**
 * 发起 HTTP 请求（对外暴露的统一入口）。
 * @param {import("axios").AxiosRequestConfig} config - axios 请求配置。
 * @returns {Promise<any>} 响应数据（已经过 normalizeResponse 处理，直接返回 data 字段）。
 */
export function request(config) {
  return httpClient.request(config);
}

/**
 * 请求拦截器：自动在请求头中附加 JWT Token。
 *
 * 若 localStorage 中存在 Token，则添加 Authorization: Bearer <token> 请求头。
 * 未登录时不添加（后端会根据接口是否需要认证决定是否拒绝）。
 *
 * @param {import("axios").InternalAxiosRequestConfig} config - 请求配置。
 * @returns {import("axios").InternalAxiosRequestConfig} 修改后的请求配置。
 */
function attachAuthHeader(config) {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;  // JWT Bearer 认证
  }
  return config;
}

/**
 * 请求拦截器错误处理（网络层错误，如请求发送失败）。
 * @param {Error} error - 错误对象。
 * @returns {Promise<never>} 始终 reject。
 */
function handleRequestError(error) {
  return Promise.reject(error);
}

/**
 * 响应拦截器：统一处理业务错误码，提取 data 字段。
 *
 * 处理逻辑：
 *   1. 若响应体没有 code 字段（如文件下载等），直接返回原始数据
 *   2. code=0：成功，返回 payload.data（调用方直接拿到业务数据）
 *   3. code=4002：Token 失效，清除本地凭证并跳转登录页
 *   4. 其他非 0：弹出错误提示，reject 错误
 *
 * @param {import("axios").AxiosResponse} response - axios 响应对象。
 * @returns {any|Promise<never>} 成功时返回 data，失败时 reject。
 */
function normalizeResponse(response) {
  const payload = response.data;
  if (!payload || typeof payload.code === "undefined") {
    // 非标准业务响应（如静态文件），直接返回
    return payload;
  }
  if (payload.code !== 0) {
    const message = payload.message || "请求失败，请稍后重试";
    if (payload.code === 4002) {
      // Token 失效：清除本地凭证，跳转到登录页
      clearAuthToken();
      window.localStorage.removeItem(USER_INFO_KEY);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    ElMessage.error(message);           // 弹出错误提示
    return Promise.reject(new Error(message));
  }
  return payload.data;  // 成功：直接返回业务数据，调用方无需再取 .data
}

/**
 * 响应拦截器错误处理（HTTP 层错误，如 404/500/网络断开）。
 *
 * @param {Error} error - axios 错误对象（含 response 字段）。
 * @returns {Promise<never>} 始终 reject，并弹出错误提示。
 */
function handleResponseError(error) {
  const message = error?.response?.data?.message || error.message || "网络异常，请稍后重试";
  ElMessage.error(message);
  return Promise.reject(error);
}
