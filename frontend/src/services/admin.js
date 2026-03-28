import { request } from "./http.js";

export function fetchAdminUsers(params) {
  return request({
    url: "/admin/users",
    method: "get",
    params,
  });
}

export function updateAdminUserRole(payload) {
  return request({
    url: "/admin/user/role",
    method: "put",
    data: payload,
  });
}

export function fetchAdminArticles(params) {
  return request({
    url: "/admin/articles",
    method: "get",
    params,
  });
}

export function reviewAdminArticle(payload) {
  return request({
    url: "/admin/article/review",
    method: "put",
    data: payload,
  });
}

export function fetchAbnormalContent(params) {
  return request({
    url: "/admin/content/abnormal",
    method: "get",
    params,
  });
}
