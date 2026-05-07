<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Inbox</p>
      <h1 class="hero-title">通知中心</h1>
      <p class="hero-subtitle">查看新的评论、回复、关注和关注作者发文提醒。</p>
    </section>

    <SectionCard title="全部通知">
      <template #actions>
        <div class="flex items-center gap-3">
          <span class="meta-text">未读 {{ unreadCount }}</span>
          <el-button class="ghost-button" size="small" :disabled="unreadCount === 0" @click="handleReadAll">
            全部标记已读
          </el-button>
        </div>
      </template>
      <div v-if="isLoading" class="skeleton-list">
        <div v-for="item in 5" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="notifications.length === 0">
        <EmptyState title="暂无通知" message="新的互动和更新会出现在这里。" />
      </div>
      <div v-else class="stack-list">
        <button
          v-for="item in notifications"
          :key="item.notification_id"
          type="button"
          class="stack-item text-left"
          @click="openNotification(item)"
        >
          <div class="flex items-center justify-between gap-3">
            <p class="stack-title">{{ item.title }}</p>
            <span class="tag-chip tag-chip--soft">{{ item.is_read ? "已读" : "未读" }}</span>
          </div>
          <p class="stack-description">{{ item.content }}</p>
          <div class="stack-meta">
            <span class="meta-text">{{ item.actor?.username || "系统" }}</span>
            <span class="meta-text">{{ formatDate(item.create_time) }}</span>
          </div>
        </button>
      </div>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { markNotificationsRead, fetchNotifications } from "../services/social.js";
import { refreshCurrentUserInfo } from "../services/user.js";

const router = useRouter();
const notifications = ref([]);
const unreadCount = ref(0);
const isLoading = ref(false);

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).replace("T", " ").slice(0, 16);
}

async function loadNotifications() {
  try {
    isLoading.value = true;
    const data = await fetchNotifications({ page: 1, page_size: 50 });
    notifications.value = data?.list || [];
    unreadCount.value = Number(data?.unread_count || 0);
    await refreshCurrentUserInfo();
  } finally {
    isLoading.value = false;
  }
}

async function handleReadAll() {
  await markNotificationsRead({ read_all: true });
  await loadNotifications();
}

async function openNotification(item) {
  if (!item.is_read) {
    await markNotificationsRead({ notification_ids: [item.notification_id] });
  }
  await refreshCurrentUserInfo();
  if (item.target_path) {
    router.push(item.target_path);
    return;
  }
  await loadNotifications();
}

onMounted(loadNotifications);
</script>
