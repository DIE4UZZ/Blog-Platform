<template>
  <div class="rank-item">
    <div class="rank-item__badge">{{ index + 1 }}</div>
    <div class="rank-item__body">
      <div class="rank-item__title">{{ item.title }}</div>
      <div class="rank-item__meta">
        <span class="meta-text">{{ metricLabel }}</span>
        <span class="rank-item__value">{{ displayValue }}</span>
      </div>
      <div class="rank-item__progress">
        <span class="rank-item__progress-fill" :style="{ width: `${progressPercent}%` }"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  metricLabel: {
    type: String,
    required: true,
  },
  metricValue: {
    type: Number,
    required: true,
  },
  maxValue: {
    type: Number,
    required: true,
  },
  isPercent: {
    type: Boolean,
    default: false,
  },
});

/**
 * Format numeric value into display text.
 * @returns {string} Display value.
 */
const displayValue = computed(() => {
  if (!props.isPercent) {
    return `${props.metricValue}`;
  }
  return `${Math.round(props.metricValue * 100)}%`;
});

/**
 * Calculate progress percent based on max value.
 * @returns {number} Progress percent.
 */
const progressPercent = computed(() => {
  if (!props.maxValue) return 0;
  return Math.min(100, Math.round((props.metricValue / props.maxValue) * 100));
});
</script>
