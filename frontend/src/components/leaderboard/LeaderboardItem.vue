<template>
  <article class="leaderboard-item">
    <div class="leaderboard-item__rank">
      <span class="rank-badge" :class="rankClass">{{ rank }}</span>
    </div>
    <div class="leaderboard-item__content">
      <router-link class="leaderboard-item__title" :to="`/articles/${item.article_id}`">
        {{ item.title }}
      </router-link>
      <p class="leaderboard-item__summary">
        {{ item.summary || "暂无摘要" }}
      </p>
      <div class="leaderboard-item__meta">
        <span v-if="item.category" class="tag-chip">{{ item.category }}</span>
        <span class="meta-text">{{ formatDate(item.create_time) }}</span>
        <span class="meta-divider"></span>
        <span class="meta-text">热度 {{ formatMetric(item.hot_value) }}</span>
        <span class="meta-text">分享 {{ formatMetric(item.share_count) }}</span>
      </div>
    </div>
    <div class="leaderboard-item__cover">
      <img v-if="item.cover" :src="item.cover" alt="" />
      <div v-else class="leaderboard-item__placeholder">No Image</div>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  rank: {
    type: Number,
    required: true,
  },
});

/**
 * Build rank badge class for top items.
 * @returns {string} Rank badge class name.
 */
const rankClass = computed(() => {
  if (props.rank === 1) return "rank-badge--top1";
  if (props.rank === 2) return "rank-badge--top2";
  if (props.rank === 3) return "rank-badge--top3";
  return "";
});

/**
 * Format datetime string into short date.
 * @param {string} value Datetime string.
 * @returns {string} Date text.
 */
function formatDate(value) {
  if (!value) return "未知时间";
  return value.split(" ")[0];
}

/**
 * Format numeric metrics into readable text.
 * @param {number} value Metric value.
 * @returns {string} Formatted metric.
 */
function formatMetric(value) {
  const safeValue = Number(value) || 0;
  if (safeValue < 10000) {
    return `${safeValue}`;
  }
  return `${(safeValue / 10000).toFixed(1)}万`;
}
</script>
