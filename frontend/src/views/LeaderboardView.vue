<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Hot Topics</p>
      <h1 class="hero-title">排行榜</h1>
      <p class="hero-subtitle">聚焦热点内容，快速发现全站热议与优质创作者。</p>
    </section>

    <div class="leaderboard-grid">
      <SectionCard title="辟谣专区">
        <template #actions>
          <el-button class="ghost-button" size="small" @click="handleRefresh">
            刷新
          </el-button>
        </template>
        <el-form class="leaderboard-filters" label-position="top">
          <el-form-item label="关键词">
            <el-input v-model="filters.keyword" placeholder="搜索标题关键词" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="filters.category" placeholder="例如：社会热点" />
          </el-form-item>
          <el-form-item label="排序">
            <el-select v-model="filters.order" placeholder="选择排序">
              <el-option label="热度优先" value="hottest" />
              <el-option label="最新发布" value="latest" />
            </el-select>
          </el-form-item>
          <el-button class="solid-button" :loading="isLoading" @click="handleSearch">
            筛选
          </el-button>
        </el-form>
        <LeaderboardList
          :list="rankList"
          :loading="isLoading"
          :total="total"
          :page="page"
          :page-size="pageSize"
          @page-change="handlePageChange"
          @refresh="handleRefresh"
        />
      </SectionCard>

      <aside class="leaderboard-side">
        <SectionCard title="大家都在搜">
          <HotSearchCard
            :list="hotSearchList"
            :loading="isHotSearchLoading"
            @refresh="handleHotSearchRefresh"
          />
        </SectionCard>
        <SectionCard title="盐作家平台">
          <div class="promo-card">
            <p class="promo-card__title">写好故事，赢高收益！</p>
            <p class="promo-card__text">加入创作者计划，解锁流量扶持与成长礼包。</p>
            <el-button class="solid-button promo-card__button">去投稿</el-button>
          </div>
        </SectionCard>
        <SectionCard title="推荐关注">
          <RecommendFollowCard :list="recommendList" />
        </SectionCard>
      </aside>
    </div>
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import LeaderboardList from "../components/leaderboard/LeaderboardList.vue";
import HotSearchCard from "../components/leaderboard/HotSearchCard.vue";
import RecommendFollowCard from "../components/leaderboard/RecommendFollowCard.vue";
import { reportBehavior } from "../services/behavior.js";
import { fetchHotSearch, fetchRankList, fetchRecommendFollow } from "../services/leaderboard.js";

const filters = reactive({
  keyword: "",
  category: "",
  order: "hottest",
});
const page = ref(1);
const pageSize = 8;
const total = ref(0);
const rankList = ref([]);
const isLoading = ref(false);
const hotSearchList = ref([]);
const hotSearchPage = ref(1);
const hotSearchSize = 8;
const isHotSearchLoading = ref(false);
const recommendList = ref([]);

/**
 * Load leaderboard list with current filters.
 * @param {boolean} resetPage Whether to reset pagination.
 * @returns {Promise<void>} No return value.
 */
async function loadRankList(resetPage) {
  if (resetPage) {
    page.value = 1;
  }
  const params = {
    page: page.value,
    page_size: pageSize,
    category: filters.category || undefined,
    keyword: filters.keyword || undefined,
    order: filters.order || undefined,
  };
  try {
    isLoading.value = true;
    const data = await fetchRankList(params);
    rankList.value = data?.list || [];
    total.value = data?.total || 0;
  } finally {
    isLoading.value = false;
  }
}

/**
 * Load hot search list.
 * @returns {Promise<void>} No return value.
 */
async function loadHotSearch() {
  try {
    isHotSearchLoading.value = true;
    const data = await fetchHotSearch({ page: hotSearchPage.value, page_size: hotSearchSize });
    hotSearchList.value = data?.list || [];
  } finally {
    isHotSearchLoading.value = false;
  }
}

/**
 * Load recommended follow list.
 * @returns {Promise<void>} No return value.
 */
async function loadRecommendList() {
  const data = await fetchRecommendFollow({ limit: 6 });
  recommendList.value = data?.list || [];
}

/**
 * Handle pagination change.
 * @param {number} value Current page.
 * @returns {void} No return value.
 */
function handlePageChange(value) {
  page.value = value;
  loadRankList(false);
}

/**
 * Trigger search with current filters.
 * @returns {void} No return value.
 */
function handleSearch() {
  if (filters.keyword.trim()) {
    reportBehavior({
      behavior_type: "search",
      keyword: filters.keyword.trim(),
    }).catch(() => {});
  }
  loadRankList(true);
}

/**
 * Refresh leaderboard list with current page.
 * @returns {void} No return value.
 */
function handleRefresh() {
  loadRankList(false);
}

/**
 * Rotate hot search list to next page.
 * @returns {void} No return value.
 */
function handleHotSearchRefresh() {
  hotSearchPage.value += 1;
  loadHotSearch();
}

/**
 * Initialize leaderboard page data.
 * @returns {void} No return value.
 */
function handleMounted() {
  loadRankList(true);
  loadHotSearch();
  loadRecommendList();
}

onMounted(handleMounted);
</script>
