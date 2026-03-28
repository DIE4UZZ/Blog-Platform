import { request } from "./http.js";

const FLUSH_INTERVAL_MS = 8000;
const MAX_QUEUE_SIZE = 20;
const MAX_RETRY_COUNT = 3;

let queue = [];
let flushTimer = null;
let flushing = false;

function normalizeBehaviorPayload(payload) {
  return {
    article_id: payload.article_id ?? null,
    behavior_type: String(payload.behavior_type || ""),
    read_duration: payload.read_duration ?? null,
    scroll_depth: payload.scroll_depth ?? null,
    keyword: payload.keyword ?? null,
    _retry_count: payload._retry_count ?? 0,
  };
}

function scheduleFlush() {
  if (flushTimer) return;
  flushTimer = window.setTimeout(() => {
    flushTimer = null;
    flushBehaviorQueue();
  }, FLUSH_INTERVAL_MS);
}

function enqueueBehavior(payload) {
  queue.push(normalizeBehaviorPayload(payload));
  if (queue.length >= MAX_QUEUE_SIZE) {
    flushBehaviorQueue();
    return;
  }
  scheduleFlush();
}

async function sendOne(payload) {
  const safePayload = { ...payload };
  delete safePayload._retry_count;
  return request({
    url: "/behavior/report",
    method: "post",
    data: safePayload,
  });
}

async function sendBatch(payloads) {
  const items = payloads.map((item) => {
    const safeItem = { ...item };
    delete safeItem._retry_count;
    return safeItem;
  });
  return request({
    url: "/behavior/report-batch",
    method: "post",
    data: { items },
  });
}

function requeueWithRetry(payload) {
  const retryCount = Number(payload._retry_count || 0) + 1;
  if (retryCount > MAX_RETRY_COUNT) return;
  queue.unshift({ ...payload, _retry_count: retryCount });
}

export async function flushBehaviorQueue() {
  if (flushing || queue.length === 0) return;
  flushing = true;
  const pending = queue;
  queue = [];
  try {
    const chunks = [];
    for (let i = 0; i < pending.length; i += MAX_QUEUE_SIZE) {
      chunks.push(pending.slice(i, i + MAX_QUEUE_SIZE));
    }
    for (const chunk of chunks) {
      try {
        await sendBatch(chunk);
      } catch (_error) {
        for (const item of chunk) {
          requeueWithRetry(item);
        }
      }
    }
  } finally {
    flushing = false;
    if (queue.length) {
      scheduleFlush();
    }
  }
}

export function reportBehavior(payload, options = {}) {
  const immediate = Boolean(options.immediate);
  if (immediate) {
    return sendOne(normalizeBehaviorPayload(payload)).catch(() => {});
  }
  enqueueBehavior(payload);
  return Promise.resolve();
}

export function trackSearch(keyword) {
  const value = String(keyword || "").trim();
  if (!value) return;
  reportBehavior({
    behavior_type: "search",
    keyword: value,
  });
}

export function trackRead({ articleId, duration, scrollDepth }) {
  if (!articleId) return;
  reportBehavior(
    {
      article_id: articleId,
      behavior_type: "read",
      read_duration: Math.max(0, Number(duration || 0)),
      scroll_depth: Number(Number(scrollDepth || 0).toFixed(2)),
    },
    { immediate: true }
  );
}

export function trackLike(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "like",
  });
}

export function trackCollect(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "collect",
  });
}

export function trackComment(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "comment",
  });
}

function sendByBeacon(payload) {
  if (!navigator.sendBeacon) return false;
  try {
    const data = { ...payload };
    delete data._retry_count;
    const blob = new Blob([JSON.stringify(data)], {
      type: "application/json",
    });
    return navigator.sendBeacon("/api/behavior/report", blob);
  } catch (_error) {
    return false;
  }
}

function flushByBeacon() {
  if (!queue.length) return;
  const pending = queue;
  queue = [];
  pending.forEach((item) => {
    const success = sendByBeacon(item);
    if (!success) {
      requeueWithRetry(item);
    }
  });
}

window.addEventListener("beforeunload", () => {
  flushByBeacon();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    flushByBeacon();
  }
});
