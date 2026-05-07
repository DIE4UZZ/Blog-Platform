import { request } from "./http.js";

export function toggleFollow(payload) {
  return request({
    url: "/follow/action",
    method: "post",
    data: payload,
  });
}

export function fetchFollowingFeed(params) {
  return request({
    url: "/feed/following",
    method: "get",
    params,
  });
}

export function fetchNotifications(params) {
  return request({
    url: "/notification/list",
    method: "get",
    params,
  });
}

export function markNotificationsRead(payload) {
  return request({
    url: "/notification/read",
    method: "put",
    data: payload,
  });
}

export function fetchFollowList(params) {
  return request({
    url: "/follow/list",
    method: "get",
    params,
  });
}
