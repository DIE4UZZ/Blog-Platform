<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Following Feed</p>
      <h1 class="hero-title">关注流</h1>
      <p class="hero-subtitle">这里聚合了你已关注作者最近发布的文章，适合持续追更。</p>
    </section>

    <SectionCard title="最新动态">
      <template #actions>
        <span class="meta-text">共 {{ total }} 篇</span>
      </template>
      <div v-if="isLoading" class="skeleton-list">
        <div v-for="item in 4" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="feedList.length === 0">
        <EmptyState title="还没有关注内容" message="先去关注一些作者，新的文章会出现在这里。" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in feedList" :key="item.article_id" class="list-card">
          <div class="list-card__meta">
            <span class="tag-chip">{{ item.category || "未分类" }}</span>
            <span class="meta-text">{{ formatDate(item.create_time) }}</span>
          </div>
          <h3 class="list-card__title">{{ item.title }}</h3>
          <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
          <div class="list-card__stats">
            <span class="list-stat">作者 {{ item.author?.username || "匿名" }}</span>
            <span class="list-stat">阅读 {{ item.view_count || 0 }}</span>
            <span class="list-stat">评论 {{ item.comment_count || 0 }}</span>
          </div>
          <div class="list-card__footer">
            <span class="meta-text">来自你关注的作者</span>
            <router-link class="text-link" :to="`/articles/${item.article_id}`">阅读文章</router-link>
          </div>
        </article>
      </div>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { fetchFollowingFeed } from "../services/social.js";

const feedList = ref([]);
const total = ref(0);
const isLoading = ref(false);

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).split(" ")[0];
}

async function loadFeed() {
  try {
    isLoading.value = true;
    const data = await fetchFollowingFeed({ page: 1, page_size: 20 });
    feedList.value = data?.list || [];
    total.value = Number(data?.total || 0);
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadFeed);
</script>
