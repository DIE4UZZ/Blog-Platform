<template>
  <div class="recommend-follow">
    <div v-if="list.length === 0">
      <EmptyState title="暂无推荐" message="稍后再试。" />
    </div>
    <div v-else class="recommend-follow__list">
      <div v-for="item in list" :key="item.user_id" class="recommend-follow__item">
        <div class="recommend-follow__info">
          <div class="recommend-follow__name">{{ item.name }}</div>
          <div class="meta-text">{{ item.desc }}</div>
        </div>
        <el-button
          class="ghost-button recommend-follow__button"
          size="small"
          @click="toggleFollow(item)"
        >
          {{ item.followed ? "已关注" : "关注" }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import EmptyState from "../EmptyState.vue";

const props = defineProps({
  list: {
    type: Array,
    required: true,
  },
});

/**
 * Toggle follow status in local list.
 * @param {Object} item Creator item.
 * @returns {void} No return value.
 */
function toggleFollow(item) {
  item.followed = !item.followed;
}
</script>
