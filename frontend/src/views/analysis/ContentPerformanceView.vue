<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Content Performance</p>
      <h1 class="hero-title">内容表现分析</h1>
      <p class="hero-subtitle">阅读量、互动率与分类热度同屏展示。</p>
    </section>

    <AnalysisNav />

    <SectionCard title="筛选条件">
      <div class="analysis-filters">
        <label class="analysis-field">
          <span class="meta-text">排行数量</span>
          <input v-model.number="filters.limit" type="number" min="3" max="20" class="analysis-input" />
        </label>
        <button
          type="button"
          class="solid-button analysis-button"
          :disabled="isLoading"
          @click="loadPerformance"
        >
          刷新数据
        </button>
      </div>
    </SectionCard>

    <div v-if="isLoading" class="skeleton-list">
      <div class="skeleton-line" v-for="item in 3" :key="item"></div>
    </div>
    <EmptyState
      v-else-if="!currentUserId"
      title="需要登录"
      message="登录后即可查看内容表现分析。"
    />
    <EmptyState
      v-else-if="articles.length === 0"
      title="暂无内容数据"
      message="发布文章后即可查看表现排行。"
    />

    <div v-else class="analysis-grid">
      <SectionCard title="表现概览">
        <div class="metric-grid">
          <div class="metric-card">
            <p class="meta-text">总阅读量</p>
            <h3 class="metric-value">{{ totalViews }}</h3>
          </div>
          <div class="metric-card">
            <p class="meta-text">平均互动率</p>
            <h3 class="metric-value">{{ formatPercent(avgEngagement) }}</h3>
          </div>
          <div class="metric-card">
            <p class="meta-text">最高阅读量</p>
            <h3 class="metric-value">{{ maxViewCount }}</h3>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="分类热度雷达图">
        <div v-if="categoryStats.length === 0" class="meta-text">暂无分类热度数据。</div>
        <div v-else ref="radarChartRef" class="analysis-chart"></div>
      </SectionCard>

      <SectionCard title="阅读量排行">
        <div class="analysis-split analysis-split--stack">
          <div class="analysis-split__list">
            <RankListItem
              v-for="(item, index) in viewRanking"
              :key="item.article_id"
              :item="item"
              :index="index"
              metric-label="阅读量"
              :metric-value="item.view_count"
              :max-value="maxViewCount"
            />
          </div>
          <div class="analysis-split__chart">
            <div ref="viewChartRef" class="analysis-chart" :style="viewChartStyle"></div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="互动率排行">
        <div class="analysis-split analysis-split--stack">
          <div class="analysis-split__list">
            <RankListItem
              v-for="(item, index) in engagementRanking"
              :key="item.article_id"
              :item="item"
              :index="index"
              metric-label="互动率"
              :metric-value="item.engagement_rate"
              :max-value="maxEngagementRate"
              is-percent
            />
          </div>
          <div class="analysis-split__chart">
            <div ref="engagementChartRef" class="analysis-chart" :style="engagementChartStyle"></div>
          </div>
        </div>
      </SectionCard>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import * as echarts from "echarts";
import AppLayout from "../../components/AppLayout.vue";
import AnalysisNav from "../../components/AnalysisNav.vue";
import SectionCard from "../../components/SectionCard.vue";
import EmptyState from "../../components/EmptyState.vue";
import RankListItem from "../../components/RankListItem.vue";
import { fetchContentPerformance } from "../../services/analysis.js";
import { fetchUserInfo } from "../../services/user.js";
import { formatPercent } from "../../utils/analysis.js";

const filters = reactive({ limit: 10 });
const articles = ref([]);
const categoryStats = ref([]);
const viewChartRef = ref(null);
const engagementChartRef = ref(null);
const radarChartRef = ref(null);
const viewChartInstance = ref(null);
const engagementChartInstance = ref(null);
const radarChartInstance = ref(null);
const isLoading = ref(false);
const currentUserId = ref(null);

const viewRanking = computed(() => [...articles.value].sort((a, b) => b.view_count - a.view_count));
const engagementRanking = computed(() => [...articles.value].sort((a, b) => b.engagement_rate - a.engagement_rate));

const totalViews = computed(() => articles.value.reduce((sum, item) => sum + (item.view_count || 0), 0));
const avgEngagement = computed(() => {
  if (!articles.value.length) return 0;
  const total = articles.value.reduce((sum, item) => sum + (item.engagement_rate || 0), 0);
  return total / articles.value.length;
});
const maxViewCount = computed(() => viewRanking.value[0]?.view_count || 0);
const maxEngagementRate = computed(() => engagementRanking.value[0]?.engagement_rate || 0);
const viewChartStyle = computed(() => {
  const count = Math.max(3, viewRanking.value.length);
  const height = Math.min(220, Math.max(140, count * 18));
  return { height: `${height}px` };
});
const engagementChartStyle = computed(() => {
  const count = Math.max(3, engagementRanking.value.length);
  const height = Math.min(220, Math.max(140, count * 18));
  return { height: `${height}px` };
});

function initCharts() {
  if (viewChartRef.value && !viewChartInstance.value) {
    viewChartInstance.value = echarts.init(viewChartRef.value);
  }
  if (engagementChartRef.value && !engagementChartInstance.value) {
    engagementChartInstance.value = echarts.init(engagementChartRef.value);
  }
  if (radarChartRef.value && !radarChartInstance.value) {
    radarChartInstance.value = echarts.init(radarChartRef.value);
  }
}

function updateViewChart() {
  if (!viewChartInstance.value) return;
  const list = viewRanking.value.slice(0, filters.limit);
  const titles = [...list].map((item) => item.title).reverse();
  const values = [...list].map((item) => item.view_count).reverse();
  viewChartInstance.value.setOption({
    grid: { left: 80, right: 30, top: 20, bottom: 20 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: titles },
    series: [
      {
        type: "bar",
        data: values,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: "#111827" },
            { offset: 1, color: "#64748b" },
          ]),
        },
        barWidth: 16,
      },
    ],
  });
}

function updateEngagementChart() {
  if (!engagementChartInstance.value) return;
  const list = engagementRanking.value.slice(0, filters.limit);
  const titles = list.map((item) => item.title);
  const values = list.map((item) => item.engagement_rate);
  engagementChartInstance.value.setOption({
    grid: { left: 40, right: 20, top: 30, bottom: 70 },
    tooltip: { trigger: "axis", valueFormatter: (value) => `${Math.round(value * 100)}%` },
    xAxis: { type: "category", data: titles, axisLabel: { rotate: 20 } },
    yAxis: { type: "value", axisLabel: { formatter: (value) => `${value * 100}%` } },
    series: [
      {
        type: "bar",
        data: values,
        barWidth: 18,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "#0f172a" },
            { offset: 1, color: "#94a3b8" },
          ]),
        },
      },
    ],
  });
}

function updateRadarChart() {
  if (!radarChartInstance.value || !categoryStats.value.length) return;
  const maxScore = Math.max(...categoryStats.value.map((item) => Number(item.hot_score || 0)), 1);
  const indicators = categoryStats.value.map((item) => ({
    name: String(item.category || "未分类"),
    max: Math.ceil(maxScore * 1.1),
  }));
  const values = categoryStats.value.map((item) => Number(item.hot_score || 0));

  radarChartInstance.value.setOption({
    tooltip: {
      trigger: "item",
      formatter() {
        return categoryStats.value
          .map((item) => `${item.category}: ${Number(item.hot_score || 0).toFixed(1)}`)
          .join("<br/>");
      },
    },
    radar: {
      indicator: indicators,
      splitNumber: 4,
      axisName: { color: "#475569" },
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.35)" } },
      splitArea: { areaStyle: { color: ["rgba(241,245,249,0.45)", "rgba(226,232,240,0.25)"] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name: "分类热度",
            areaStyle: { color: "rgba(59, 130, 246, 0.25)" },
            lineStyle: { color: "#2563eb", width: 2 },
            itemStyle: { color: "#1d4ed8" },
          },
        ],
      },
    ],
    animationDuration: 700,
  });
}

function resizeCharts() {
  if (viewChartInstance.value) viewChartInstance.value.resize();
  if (engagementChartInstance.value) engagementChartInstance.value.resize();
  if (radarChartInstance.value) radarChartInstance.value.resize();
}

function disposeCharts() {
  if (viewChartInstance.value) {
    viewChartInstance.value.dispose();
    viewChartInstance.value = null;
  }
  if (engagementChartInstance.value) {
    engagementChartInstance.value.dispose();
    engagementChartInstance.value = null;
  }
  if (radarChartInstance.value) {
    radarChartInstance.value.dispose();
    radarChartInstance.value = null;
  }
}

async function loadCurrentUser() {
  try {
    const data = await fetchUserInfo();
    currentUserId.value = data?.user_id || null;
  } catch (_error) {
    currentUserId.value = null;
  }
}

async function loadPerformance() {
  if (!currentUserId.value) return;
  let hasError = false;
  try {
    disposeCharts();
    isLoading.value = true;
    const data = await fetchContentPerformance({
      user_id: currentUserId.value,
      limit: filters.limit,
    });
    articles.value = data?.articles || [];
    categoryStats.value = data?.category_stats || [];
  } catch (_error) {
    hasError = true;
  } finally {
    isLoading.value = false;
  }

  if (hasError || articles.value.length === 0) return;
  await nextTick();
  initCharts();
  updateViewChart();
  updateEngagementChart();
  updateRadarChart();
  resizeCharts();
}

async function handleMounted() {
  initCharts();
  window.addEventListener("resize", resizeCharts);
  await loadCurrentUser();
  await loadPerformance();
}

onMounted(handleMounted);
onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeCharts);
  disposeCharts();
});
</script>
