<template>
  <div class="leaderboard-list">
    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-line" v-for="item in 5" :key="item"></div>
    </div>
    <div v-else-if="list.length === 0">
      <EmptyState title="暂无排行" message="稍后再试或调整筛选条件。" />
    </div>
    <div v-else class="leaderboard-list__items">
      <LeaderboardItem
        v-for="(item, index) in list"
        :key="item.article_id"
        :item="item"
        :rank="rankStart + index + 1"
      />
    </div>
    <div class="leaderboard-list__footer">
      <el-button class="ghost-button" :loading="loading" @click="handleRefresh">
        刷新榜单
      </el-button>
      <el-pagination
        v-if="total > 0"
        background
        :current-page="page"
        :page-size="pageSize"
        layout="prev, pager, next"
        :total="total"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import EmptyState from "../EmptyState.vue";
import LeaderboardItem from "./LeaderboardItem.vue";

const props = defineProps({
  list: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  total: {
    type: Number,
    default: 0,
  },
  page: {
    type: Number,
    default: 1,
  },
  pageSize: {
    type: Number,
    default: 10,
  },
});

const emit = defineEmits(["page-change", "refresh"]);

/**
 * Calculate rank offset for pagination.
 * @returns {number} Rank offset.
 */
const rankStart = computed(() => (props.page - 1) * props.pageSize);

/**
 * Emit page change event.
 * @param {number} value Target page.
 * @returns {void} No return value.
 */
function handlePageChange(value) {
  emit("page-change", value);
}

/**
 * Emit refresh event.
 * @returns {void} No return value.
 */
function handleRefresh() {
  emit("refresh");
}
</script>
