import axios from "axios";
import { ElMessage } from "element-plus";

const TOKEN_KEY = "blog_platform_token";
const USER_INFO_KEY = "blog_platform_user_info";

export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

function createHttpClient() {
  const client = axios.create({
    baseURL: "/api",
    timeout: 12000,
    headers: {
      "Content-Type": "application/json",
    },
  });
  client.interceptors.request.use(attachAuthHeader, handleRequestError);
  client.interceptors.response.use(normalizeResponse, handleResponseError);
  return client;
}

const httpClient = createHttpClient();

export function request(config) {
  return httpClient.request(config);
}

function attachAuthHeader(config) {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

function handleRequestError(error) {
  return Promise.reject(error);
}

function normalizeResponse(response) {
  const payload = response.data;
  if (!payload || typeof payload.code === "undefined") {
    return payload;
  }
  if (payload.code !== 0) {
    const message = payload.message || "请求失败，请稍后重试";
    if (payload.code === 4002) {
      clearAuthToken();
      window.localStorage.removeItem(USER_INFO_KEY);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    ElMessage.error(message);
    return Promise.reject(new Error(message));
  }
  return payload.data;
}

function handleResponseError(error) {
  const message = error?.response?.data?.message || error.message || "网络异常，请稍后重试";
  ElMessage.error(message);
  return Promise.reject(error);
}
