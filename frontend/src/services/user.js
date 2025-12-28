import { request } from "./http.js";

/**
 * Register a new user with email and password.
 * @param {{ email: string, password: string }} payload Registration payload.
 * @returns {Promise<{ user_id?: number }>} API response data.
 */
export function registerUser(payload) {
  return request({
    url: "/user/register",
    method: "post",
    data: payload,
  });
}

/**
 * Login with email and password to obtain token.
 * @param {{ email: string, password: string }} payload Login payload.
 * @returns {Promise<{ token?: string, user_id?: number }>} API response data.
 */
export function loginUser(payload) {
  return request({
    url: "/user/login",
    method: "post",
    data: payload,
  });
}
