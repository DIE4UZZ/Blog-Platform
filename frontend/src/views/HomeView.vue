<template>
  <AppLayout>
    <section class="hero-block">
      <p class="hero-kicker">Curated Reading</p>
      <h1 class="hero-title">从这里开始读今天值得看的内容</h1>
      <p class="hero-subtitle">
       你可以直接阅读推荐文章，也可以通过关键词、分类和标签快速筛选。
      </p>
      <div class="hero-actions">
        <router-link class="solid-button" to="/articles">浏览全部文章</router-link>
        <router-link class="ghost-button" to="/editor">开始创作</router-link>
      </div>
    </section>

    <SectionCard title="探索内容">
      <p class="section-intro">
        通过关键词、分类和标签快速切换推荐视角，筛选结果会直接作用于当前内容流。
      </p>
      <el-form class="filter-bar" label-position="top">
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索标题与正文关键词" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="filters.category" placeholder="如：技术、生活" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filters.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <el-button class="solid-button" :loading="isListLoading" @click="handleSearch">搜索</el-button>
      </el-form>
    </SectionCard>

    <div class="home-grid">
      <SectionCard :title="isSearching ? '搜索结果' : '个性化推荐'">
        <template #actions>
          <span class="meta-text">{{ total }} 篇内容</span>
        </template>
        <div v-if="isListLoading" class="skeleton-list">
          <div v-for="item in 4" :key="item" class="skeleton-line"></div>
        </div>
        <div v-else-if="articleList.length === 0">
          <EmptyState title="暂无内容" message="尝试调整筛选条件。" />
        </div>
        <div v-else class="card-list">
          <article v-for="item in articleList" :key="item.article_id" class="list-card">
            <div class="list-card__meta">
              <span class="tag-chip">{{ item.category || "未分类" }}</span>
              <span class="meta-text">{{ formatDate(item.create_time) }}</span>
            </div>
            <h3 class="list-card__title">{{ item.title }}</h3>
            <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
            <div v-if="item.tags?.length" class="tag-list">
              <span
                v-for="tag in item.tags.slice(0, 4)"
                :key="`${item.article_id}-${tag}`"
                class="tag-chip tag-chip--soft"
              >
                {{ tag }}
              </span>
            </div>
            <div class="list-card__stats">
              <span class="list-stat">阅读 {{ item.view_count || 0 }}</span>
              <span class="list-stat">点赞 {{ item.like_count || 0 }}</span>
              <span class="list-stat">评论 {{ item.comment_count || 0 }}</span>
            </div>
            <div class="list-card__footer">
              <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
              <div class="list-actions list-actions--aligned">
                <el-button class="ghost-button ghost-button--compact" @click="handleLike(item)">
                  赞 {{ item.like_count || 0 }}
                </el-button>
                <router-link class="ghost-button ghost-button--compact" :to="`/articles/${item.article_id}`">
                  阅读
                </router-link>
              </div>
            </div>
          </article>
        </div>
        <div class="mt-6 flex items-center justify-center">
          <el-button
            class="ghost-button"
            :disabled="articleList.length >= total"
            :loading="isLoadingMore"
            @click="loadMore"
          >
            加载更多
          </el-button>
        </div>
      </SectionCard>

      <div class="sidebar-stack">
        <SectionCard title="热门文章">
          <div v-if="isHotLoading" class="skeleton-list">
            <div v-for="item in 4" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="hotList.length === 0">
            <EmptyState title="暂无热门" message="稍后再试" />
          </div>
          <div v-else class="stack-list">
            <router-link
              v-for="item in hotList"
              :key="item.article_id"
              class="stack-item"
              :to="`/articles/${item.article_id}`"
            >
              <p class="stack-title">{{ item.title }}</p>
              <p class="stack-description">按阅读热度聚合，适合快速查看站内热点。</p>
              <div class="stack-meta">
                <span class="meta-text">{{ item.category || "未分类" }}</span>
                <span class="meta-text">阅读 {{ item.view_count || 0 }}</span>
              </div>
            </router-link>
          </div>
        </SectionCard>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { fetchArticleList, toggleLike } from "../services/article.js";
import { fetchRecommendList } from "../services/recommend.js";
import { trackLike, trackSearch } from "../services/behavior.js";

const filters = reactive({
  keyword: "",
  category: "",
  tags: "",
});
const page = ref(1);
const pageSize = 6;
const total = ref(0);
const articleList = ref([]);
const hotList = ref([]);
const isListLoading = ref(false);
const isLoadingMore = ref(false);
const isHotLoading = ref(false);

const isSearching = computed(() => {
  return Boolean(filters.keyword.trim() || filters.category.trim() || filters.tags.trim());
});

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).split(" ")[0];
}

async function loadArticleList(resetPage) {
  if (resetPage) {
    page.value = 1;
    articleList.value = [];
  }
  const loadingFlag = resetPage ? isListLoading : isLoadingMore;
  try {
    loadingFlag.value = true;
    const data = isSearching.value
      ? await fetchArticleList({
          page: page.value,
          page_size: pageSize,
          category: filters.category || undefined,
          tags: filters.tags || undefined,
          keyword: filters.keyword || undefined,
          order: "latest",
        })
      : await fetchRecommendList({
          page: page.value,
          page_size: pageSize,
        });
    const list = data?.list || [];
    total.value = data?.total || 0;
    articleList.value = resetPage ? list : [...articleList.value, ...list];
  } finally {
    loadingFlag.value = false;
  }
}

async function loadHotList() {
  try {
    isHotLoading.value = true;
    const data = await fetchArticleList({ page: 1, page_size: 6, order: "hottest" });
    hotList.value = data?.list || [];
  } finally {
    isHotLoading.value = false;
  }
}

async function handleSearch() {
  trackSearch(filters.keyword);
  await loadArticleList(true);
}

async function loadMore() {
  if (articleList.value.length >= total.value) return;
  page.value += 1;
  await loadArticleList(false);
}

async function handleLike(item) {
  const action = item.is_liked ? "unlike" : "like";
  const data = await toggleLike({ article_id: item.article_id, action });
  item.like_count = data?.like_count ?? item.like_count;
  item.is_liked = data?.is_liked ?? !item.is_liked;
  if (action === "like") {
    trackLike(item.article_id);
  }
}

onMounted(() => {
  loadArticleList(true);
  loadHotList();
});
</script>
