<template>
  <div class="hot-search">
    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-line" v-for="item in 5" :key="item"></div>
    </div>
    <div v-else-if="list.length === 0">
      <EmptyState title="暂无热搜" message="还没有热词数据。" />
    </div>
    <div v-else class="hot-search__list">
      <div v-for="(item, index) in list" :key="item.keyword" class="hot-search__item">
        <span class="hot-search__rank">{{ index + 1 }}</span>
        <span class="hot-search__keyword">{{ item.keyword }}</span>
        <span v-if="item.is_hot" class="hot-search__badge">热</span>
        <span class="hot-search__count">{{ formatCount(item.count) }}</span>
      </div>
    </div>
    <el-button class="ghost-button hot-search__refresh" @click="handleRefresh">
      换一换
    </el-button>
  </div>
</template>

<script setup>
import EmptyState from "../EmptyState.vue";

const props = defineProps({
  list: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["refresh"]);

/**
 * Emit refresh event for hot search list.
 * @returns {void} No return value.
 */
function handleRefresh() {
  emit("refresh");
}

/**
 * Format count display.
 * @param {number} value Count value.
 * @returns {string} Display string.
 */
function formatCount(value) {
  const safeValue = Number(value) || 0;
  if (safeValue < 10000) {
    return `${safeValue}`;
  }
  return `${(safeValue / 10000).toFixed(1)}万`;
}
</script>
