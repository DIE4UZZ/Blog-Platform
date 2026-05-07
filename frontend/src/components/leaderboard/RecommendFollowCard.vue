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
          :loading="loadingId === item.user_id"
          @click="toggleFollowState(item)"
        >
          {{ item.followed ? "已关注" : "关注" }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import EmptyState from "../EmptyState.vue";
import { toggleFollow } from "../../services/social.js";
import { refreshCurrentUserInfo } from "../../services/user.js";

defineProps({
  list: {
    type: Array,
    required: true,
  },
});

const loadingId = ref(null);

async function toggleFollowState(item) {
  const action = item.followed ? "unfollow" : "follow";
  try {
    loadingId.value = item.user_id;
    const data = await toggleFollow({
      target_user_id: item.user_id,
      action,
    });
    item.followed = Boolean(data?.is_followed);
    item.follower_count = Number(data?.follower_count || item.follower_count || 0);
    await refreshCurrentUserInfo();
  } finally {
    loadingId.value = null;
  }
}
</script>
