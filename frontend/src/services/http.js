import axios from "axios";
import { ElMessage } from "element-plus";

const TOKEN_KEY = "blog_platform_token";

/**
 * Read auth token from localStorage.
 * @returns {string | null} Stored token value.
 */
export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

/**
 * Persist auth token to localStorage.
 * @param {string} token Token value to store.
 * @returns {void} No return value.
 */
export function setAuthToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove auth token from localStorage.
 * @returns {void} No return value.
 */
export function clearAuthToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

/**
 * Create a configured Axios instance.
 * @returns {import("axios").AxiosInstance} Axios client.
 */
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

/**
 * Perform an HTTP request using the shared Axios instance.
 * @param {import("axios").AxiosRequestConfig} config Axios request configuration.
 * @returns {Promise<any>} Normalized response payload.
 */
export function request(config) {
  return httpClient.request(config);
}

/**
 * Attach authorization header when token exists.
 * @param {import("axios").InternalAxiosRequestConfig} config Axios config.
 * @returns {import("axios").InternalAxiosRequestConfig} Updated config.
 */
function attachAuthHeader(config) {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

/**
 * Forward request error.
 * @param {any} error Axios request error.
 * @returns {Promise<never>} Rejected promise.
 */
function handleRequestError(error) {
  return Promise.reject(error);
}

/**
 * Normalize API response with unified payload format.
 * @param {import("axios").AxiosResponse} response Axios response.
 * @returns {any} Normalized response data.
 */
function normalizeResponse(response) {
  const payload = response.data;
  if (!payload || typeof payload.code === "undefined") {
    return payload;
  }
  if (payload.code !== 0) {
    const message = payload.message || "请求失败，请稍后重试。";
    ElMessage.error(message);
    return Promise.reject(new Error(message));
  }
  return payload.data;
}

/**
 * Handle response error and surface message.
 * @param {any} error Axios error.
 * @returns {Promise<never>} Rejected promise.
 */
function handleResponseError(error) {
  const message =
    error?.response?.data?.message || error.message || "网络异常，请稍后重试。";
  ElMessage.error(message);
  return Promise.reject(error);
}
