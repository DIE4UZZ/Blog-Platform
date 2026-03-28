<template>
  <AppLayout>
    <SectionCard title="文章发现">
      <el-form class="filter-bar" label-position="top">
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索标题或内容关键字" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="filters.category" placeholder="例如：技术/生活" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filters.tags" placeholder="以逗号分隔多个标签" />
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="filters.order" placeholder="选择排序">
            <el-option label="最新" value="latest" />
            <el-option label="最热" value="hottest" />
          </el-select>
        </el-form-item>
        <el-button class="solid-button" :loading="isLoading" @click="handleSearch">
          搜索
        </el-button>
      </el-form>

      <div v-if="isLoading" class="skeleton-list">
        <div class="skeleton-line" v-for="item in 5" :key="item"></div>
      </div>
      <div v-else-if="articles.length === 0">
        <EmptyState title="没有找到文章" message="尝试更换关键词或筛选条件。" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in articles" :key="item.article_id" class="list-card">
          <div class="list-card__meta">
            <span class="tag-chip">{{ item.category || "未分类" }}</span>
            <span class="meta-text">{{ formatDate(item.create_time) }}</span>
          </div>
          <h3 class="list-card__title">{{ item.title }}</h3>
          <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
          <div class="list-card__footer">
            <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
            <router-link class="text-link" :to="`/articles/${item.article_id}`">
              阅读文章
            </router-link>
          </div>
        </article>
      </div>

      <div class="mt-6 flex items-center justify-center">
        <el-button
          class="ghost-button"
          :disabled="articles.length >= total"
          :loading="isLoadingMore"
          @click="loadMore"
        >
          加载更多
        </el-button>
      </div>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { fetchArticleList } from "../services/article.js";
import { trackSearch } from "../services/behavior.js";

const filters = reactive({
  keyword: "",
  category: "",
  tags: "",
  order: "latest",
});
const page = ref(1);
const pageSize = 8;
const total = ref(0);
const articles = ref([]);
const isLoading = ref(false);
const isLoadingMore = ref(false);

/**
 * Format datetime string to readable date.
 * @param {string} value Datetime string.
 * @returns {string} Formatted date text.
 */
function formatDate(value) {
  if (!value) return "未知时间";
  return value.split(" ")[0];
}

/**
 * Load article list with current filters.
 * @param {boolean} resetPage Whether to reset pagination.
 * @returns {Promise<void>} No return value.
 */
async function loadArticles(resetPage) {
  if (resetPage) {
    page.value = 1;
    articles.value = [];
  }
  const params = {
    page: page.value,
    page_size: pageSize,
    category: filters.category || undefined,
    tags: filters.tags || undefined,
    keyword: filters.keyword || undefined,
    order: filters.order || undefined,
  };
  const loadingFlag = resetPage ? isLoading : isLoadingMore;
  try {
    loadingFlag.value = true;
    const data = await fetchArticleList(params);
    const list = data?.list || [];
    total.value = data?.total || 0;
    if (resetPage) {
      articles.value = list;
    } else {
      articles.value = [...articles.value, ...list];
    }
  } finally {
    loadingFlag.value = false;
  }
}

/**
 * Trigger search with current filters.
 * @returns {Promise<void>} No return value.
 */
async function handleSearch() {
  trackSearch(filters.keyword);
  await loadArticles(true);
}

/**
 * Load next page of articles.
 * @returns {Promise<void>} No return value.
 */
async function loadMore() {
  if (articles.value.length >= total.value) return;
  page.value += 1;
  await loadArticles(false);
}

/**
 * Initialize article list loading.
 * @returns {void} No return value.
 */
function handleMounted() {
  loadArticles(true);
}

onMounted(handleMounted);
</script>
