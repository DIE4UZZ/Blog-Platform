/**
 * services/behavior.js —— 用户行为上报模块
 *
 * 负责收集并上报用户行为数据，供后端数据分析和推荐系统使用。
 * 支持的行为类型：
 *   - read       : 阅读文章（含阅读时长和滚动深度）
 *   - like       : 点赞文章
 *   - collect    : 收藏文章
 *   - comment    : 评论文章
 *   - search     : 搜索关键词
 *   - page_view  : 页面访问
 *   - page_leave : 页面离开
 *
 * 性能优化设计（批量上报 + 队列机制）：
 *   1. 行为数据先进入内存队列（queue），不立即发送
 *   2. 每 8 秒（FLUSH_INTERVAL_MS）自动批量发送一次
 *   3. 队列满 20 条（MAX_QUEUE_SIZE）时立即触发发送
 *   4. 发送失败时最多重试 3 次（MAX_RETRY_COUNT）
 *   5. 页面关闭/隐藏时使用 navigator.sendBeacon 确保数据不丢失
 *
 * 特殊行为（如阅读完成）可设置 immediate=true 立即发送，不走队列。
 */

import { request } from "./http.js";

// 队列自动刷新间隔（毫秒）
const FLUSH_INTERVAL_MS = 8000;
// 队列最大容量（超过时立即触发发送）
const MAX_QUEUE_SIZE = 20;
// 发送失败最大重试次数
const MAX_RETRY_COUNT = 3;

// 行为数据内存队列
let queue = [];
// 定时刷新的 timer ID
let flushTimer = null;
// 是否正在发送中（防止并发发送）
let flushing = false;

/**
 * 标准化行为数据格式，确保所有字段都有默认值。
 *
 * @param {Object} payload - 原始行为数据。
 * @returns {Object} 标准化后的行为数据（含 _retry_count 内部字段）。
 */
function normalizeBehaviorPayload(payload) {
  return {
    article_id: payload.article_id ?? null,           // 关联文章 ID（非文章行为时为 null）
    behavior_type: String(payload.behavior_type || ""),
    read_duration: payload.read_duration ?? null,     // 阅读时长（秒）
    scroll_depth: payload.scroll_depth ?? null,       // 滚动深度（0~1 的小数）
    keyword: payload.keyword ?? null,                 // 搜索关键词或页面路径
    _retry_count: payload._retry_count ?? 0,          // 内部重试计数（不上报给服务端）
  };
}

/**
 * 启动定时刷新任务（若已有定时器则不重复创建）。
 *
 * 每 FLUSH_INTERVAL_MS 毫秒后自动调用 flushBehaviorQueue 发送队列数据。
 */
function scheduleFlush() {
  if (flushTimer) return;  // 已有定时器，不重复创建
  flushTimer = window.setTimeout(() => {
    flushTimer = null;
    flushBehaviorQueue();
  }, FLUSH_INTERVAL_MS);
}

/**
 * 将行为数据加入队列，并在必要时触发立即发送。
 *
 * 若队列已满（>= MAX_QUEUE_SIZE），立即触发发送；
 * 否则启动定时器，等待下次批量发送。
 *
 * @param {Object} payload - 行为数据（未标准化）。
 */
function enqueueBehavior(payload) {
  queue.push(normalizeBehaviorPayload(payload));
  if (queue.length >= MAX_QUEUE_SIZE) {
    // 队列已满，立即发送
    flushBehaviorQueue();
    return;
  }
  scheduleFlush();  // 启动定时发送
}

/**
 * 发送单条行为数据（立即模式使用）。
 *
 * 发送前会移除内部字段 _retry_count，避免污染服务端数据。
 *
 * @param {Object} payload - 标准化后的行为数据。
 * @returns {Promise<void>} 发送结果。
 */
async function sendOne(payload) {
  const safePayload = { ...payload };
  delete safePayload._retry_count;  // 移除内部重试计数字段
  return request({
    url: "/behavior/report",
    method: "post",
    data: safePayload,
  });
}

/**
 * 批量发送行为数据（队列模式使用）。
 *
 * 将多条行为数据打包为一个请求发送，减少 HTTP 请求次数。
 *
 * @param {Object[]} payloads - 标准化后的行为数据数组。
 * @returns {Promise<void>} 发送结果。
 */
async function sendBatch(payloads) {
  const items = payloads.map((item) => {
    const safeItem = { ...item };
    delete safeItem._retry_count;  // 移除内部重试计数字段
    return safeItem;
  });
  return request({
    url: "/behavior/report-batch",
    method: "post",
    data: { items },
  });
}

/**
 * 将发送失败的行为数据重新加入队列头部（用于重试）。
 *
 * 超过最大重试次数（MAX_RETRY_COUNT）的数据会被丢弃，避免无限重试。
 *
 * @param {Object} payload - 发送失败的行为数据（含 _retry_count）。
 */
function requeueWithRetry(payload) {
  const retryCount = Number(payload._retry_count || 0) + 1;
  if (retryCount > MAX_RETRY_COUNT) return;  // 超过最大重试次数，丢弃
  queue.unshift({ ...payload, _retry_count: retryCount });  // 加入队列头部（优先重试）
}

/**
 * 将队列中的所有行为数据批量发送到服务端。
 *
 * 处理流程：
 *   1. 检查是否正在发送中（防止并发）
 *   2. 取出当前队列，重置为空（新数据继续入队）
 *   3. 按 MAX_QUEUE_SIZE 分块，逐块发送
 *   4. 发送失败的块，逐条重新入队（带重试计数）
 *   5. 发送完成后，若队列仍有数据，重新启动定时器
 *
 * @returns {Promise<void>}
 */
export async function flushBehaviorQueue() {
  if (flushing || queue.length === 0) return;  // 正在发送中或队列为空，跳过
  flushing = true;
  const pending = queue;  // 取出当前队列
  queue = [];             // 重置队列（新数据继续入队，不影响本次发送）
  try {
    // 按 MAX_QUEUE_SIZE 分块发送
    const chunks = [];
    for (let i = 0; i < pending.length; i += MAX_QUEUE_SIZE) {
      chunks.push(pending.slice(i, i + MAX_QUEUE_SIZE));
    }
    for (const chunk of chunks) {
      try {
        await sendBatch(chunk);
      } catch (_error) {
        // 发送失败：逐条重新入队（带重试计数）
        for (const item of chunk) {
          requeueWithRetry(item);
        }
      }
    }
  } finally {
    flushing = false;
    if (queue.length) {
      scheduleFlush();  // 若队列仍有数据（重试数据），重新启动定时器
    }
  }
}

/**
 * 上报用户行为（对外暴露的主要接口）。
 *
 * 两种模式：
 *   - 普通模式（默认）：加入队列，等待批量发送（性能优先）
 *   - 立即模式（immediate=true）：立即发送，不走队列（数据准确性优先）
 *
 * @param {Object} payload - 行为数据。
 * @param {{ immediate?: boolean }} options - 选项。
 *   - immediate: true 时立即发送（适用于阅读完成等关键行为）
 * @returns {Promise<void>}
 */
export function reportBehavior(payload, options = {}) {
  const immediate = Boolean(options.immediate);
  if (immediate) {
    // 立即发送模式：直接调用 sendOne，忽略错误（静默失败）
    return sendOne(normalizeBehaviorPayload(payload)).catch(() => {});
  }
  enqueueBehavior(payload);  // 加入队列，等待批量发送
  return Promise.resolve();
}

/**
 * 上报搜索行为（便捷函数）。
 *
 * @param {string} keyword - 搜索关键词（空字符串时忽略）。
 */
export function trackSearch(keyword) {
  const value = String(keyword || "").trim();
  if (!value) return;  // 空关键词不上报
  reportBehavior({
    behavior_type: "search",
    keyword: value,
  });
}

/**
 * 上报文章阅读行为（便捷函数，立即发送）。
 *
 * 使用立即模式发送，确保用户离开页面时阅读数据不丢失。
 * 阅读数据用于：
 *   - 更新文章阅读量统计
 *   - 记录用户阅读历史
 *   - 训练个性化推荐模型
 *
 * @param {{ articleId: number|string, duration: number, scrollDepth: number }} param0 - 阅读数据。
 *   - articleId: 文章 ID
 *   - duration: 阅读时长（秒）
 *   - scrollDepth: 滚动深度（0~1，1 表示阅读到底部）
 */
export function trackRead({ articleId, duration, scrollDepth }) {
  if (!articleId) return;
  reportBehavior(
    {
      article_id: articleId,
      behavior_type: "read",
      read_duration: Math.max(0, Number(duration || 0)),                    // 确保非负
      scroll_depth: Number(Number(scrollDepth || 0).toFixed(2)),            // 保留 2 位小数
    },
    { immediate: true }  // 立即发送，确保数据不丢失
  );
}

/**
 * 上报点赞行为（便捷函数）。
 * @param {number|string} articleId - 被点赞的文章 ID。
 */
export function trackLike(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "like",
  });
}

/**
 * 上报收藏行为（便捷函数）。
 * @param {number|string} articleId - 被收藏的文章 ID。
 */
export function trackCollect(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "collect",
  });
}

/**
 * 上报评论行为（便捷函数）。
 * @param {number|string} articleId - 被评论的文章 ID。
 */
export function trackComment(articleId) {
  if (!articleId) return;
  reportBehavior({
    article_id: articleId,
    behavior_type: "comment",
  });
}

/**
 * 使用 navigator.sendBeacon 发送单条行为数据（页面关闭时使用）。
 *
 * sendBeacon 的优势：即使页面正在关闭，浏览器也会保证数据发送完成。
 * 普通的 fetch/axios 在页面关闭时可能被中断。
 *
 * @param {Object} payload - 行为数据。
 * @returns {boolean} 是否成功加入发送队列（不代表服务端已收到）。
 */
function sendByBeacon(payload) {
  if (!navigator.sendBeacon) return false;  // 浏览器不支持 sendBeacon
  try {
    const data = { ...payload };
    delete data._retry_count;  // 移除内部字段
    const blob = new Blob([JSON.stringify(data)], {
      type: "application/json",
    });
    return navigator.sendBeacon("/api/behavior/report", blob);
  } catch (_error) {
    return false;
  }
}

/**
 * 使用 sendBeacon 批量发送队列中的所有数据（页面关闭时调用）。
 *
 * 逐条发送（sendBeacon 不支持批量），发送失败的数据重新入队（但页面关闭后队列会丢失）。
 */
function flushByBeacon() {
  if (!queue.length) return;
  const pending = queue;
  queue = [];
  pending.forEach((item) => {
    const success = sendByBeacon(item);
    if (!success) {
      requeueWithRetry(item);  // 发送失败，重新入队（页面关闭后会丢失）
    }
  });
}

// ===== 页面生命周期事件监听 =====

/**
 * 页面关闭前（beforeunload）：使用 sendBeacon 发送剩余队列数据。
 * 确保用户关闭标签页时，未发送的行为数据不丢失。
 */
window.addEventListener("beforeunload", () => {
  flushByBeacon();
});

/**
 * 页面可见性变化（visibilitychange）：页面切换到后台时发送队列数据。
 * 处理用户切换标签页或最小化浏览器的场景。
 */
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    flushByBeacon();  // 页面进入后台，立即发送队列数据
  }
});
