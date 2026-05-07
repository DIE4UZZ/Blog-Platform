import { request } from "./http.js";

export function fetchCollections(params) {
  return request({
    url: "/library/collections",
    method: "get",
    params,
  });
}

export function fetchReadHistory(params) {
  return request({
    url: "/library/history",
    method: "get",
    params,
  });
}

export function fetchReadLater(params) {
  return request({
    url: "/library/read-later",
    method: "get",
    params,
  });
}

export function toggleReadLater(payload) {
  return request({
    url: "/library/read-later",
    method: "post",
    data: payload,
  });
}
