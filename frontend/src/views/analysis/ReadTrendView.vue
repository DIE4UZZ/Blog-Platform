<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Read Trend</p>
      <h1 class="hero-title">阅读趋势分析</h1>
      <p class="hero-subtitle">同屏展示 PV、UV、阅读时长与滚动深度，支持按日/周/月统计。</p>
    </section>

    <AnalysisNav />

    <SectionCard title="筛选条件">
      <div class="analysis-filters">
        <label class="analysis-field">
          <span class="meta-text">开始日期</span>
          <input v-model="filters.start_date" type="date" class="analysis-input" />
        </label>
        <label class="analysis-field">
          <span class="meta-text">结束日期</span>
          <input v-model="filters.end_date" type="date" class="analysis-input" />
        </label>
        <label class="analysis-field">
          <span class="meta-text">统计粒度</span>
          <select v-model="filters.granularity" class="analysis-input">
            <option value="day">按日</option>
            <option value="week">按周</option>
            <option value="month">按月</option>
          </select>
        </label>
        <button type="button" class="solid-button analysis-button" :disabled="isLoading" @click="loadTrend">
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
      message="登录后即可查看阅读趋势分析。"
    />
    <EmptyState
      v-else-if="trendData.dates.length === 0"
      title="暂无趋势数据"
      message="请调整时间范围或等待数据积累。"
    />

    <div v-else class="analysis-grid">
      <SectionCard title="PV / UV / 阅读时长 / 滚动深度">
        <div class="metric-hero-grid">
          <div class="metric-hero metric-hero--read">
            <div class="metric-hero__head">
              <div class="metric-hero__icon metric-hero__icon--read"></div>
              <div>
                <p class="metric-hero__label">总 PV</p>
                <h3 class="metric-hero__value">{{ formatNumber(totalPv) }}</h3>
              </div>
            </div>
            <div class="metric-hero__meta">
              <span>峰值 {{ formatNumber(maxPv) }}</span>
              <span>最新 {{ formatNumber(latestPv) }}</span>
            </div>
            <div class="metric-hero__bar">
              <span class="metric-hero__bar-fill" :style="{ width: `${pvProgress}%` }"></span>
            </div>
          </div>

          <div class="metric-hero">
            <div class="metric-hero__head">
              <div class="metric-hero__icon"></div>
              <div>
                <p class="metric-hero__label">总 UV（登录用户）</p>
                <h3 class="metric-hero__value">{{ formatNumber(totalUv) }}</h3>
              </div>
            </div>
            <div class="metric-hero__meta">
              <span>峰值 {{ formatNumber(maxUv) }}</span>
              <span>最新 {{ formatNumber(latestUv) }}</span>
            </div>
            <div class="metric-hero__bar">
              <span class="metric-hero__bar-fill" :style="{ width: `${uvProgress}%` }"></span>
            </div>
          </div>

          <div class="metric-hero metric-hero--duration">
            <div class="metric-hero__head">
              <div class="metric-hero__icon metric-hero__icon--duration"></div>
              <div>
                <p class="metric-hero__label">平均阅读时长</p>
                <h3 class="metric-hero__value">{{ formatDuration(avgDuration) }}</h3>
              </div>
            </div>
            <div class="metric-hero__meta">
              <span>峰值 {{ formatDuration(maxDuration) }}</span>
              <span>最新 {{ formatDuration(latestDuration) }}</span>
            </div>
            <div class="metric-hero__bar">
              <span
                class="metric-hero__bar-fill metric-hero__bar-fill--cool"
                :style="{ width: `${durationProgress}%` }"
              ></span>
            </div>
          </div>

          <div class="metric-hero metric-hero--depth">
            <div class="metric-hero__head">
              <div class="metric-hero__icon metric-hero__icon--depth"></div>
              <div>
                <p class="metric-hero__label">平均滚动深度</p>
                <h3 class="metric-hero__value">{{ formatDepth(avgScrollDepth) }}</h3>
              </div>
            </div>
            <div class="metric-hero__meta">
              <span>峰值 {{ formatDepth(maxScrollDepth) }}</span>
              <span>最新 {{ formatDepth(latestScrollDepth) }}</span>
            </div>
            <div class="metric-hero__bar">
              <span
                class="metric-hero__bar-fill metric-hero__bar-fill--depth"
                :style="{ width: `${scrollDepthProgress}%` }"
              ></span>
            </div>
          </div>
        </div>
        <div ref="chartRef" class="analysis-chart"></div>
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
import { fetchReadTrend } from "../../services/analysis.js";
import { fetchUserInfo } from "../../services/user.js";
import { createDefaultRange } from "../../utils/analysis.js";

const defaultRange = createDefaultRange(14);
const filters = reactive({
  start_date: defaultRange.start,
  end_date: defaultRange.end,
  granularity: "day",
});

const trendData = reactive({
  dates: [],
  read_counts: [],
  uv_counts: [],
  total_pv: 0,
  total_uv: 0,
  avg_read_duration: [],
  avg_scroll_depth: [],
});

const chartRef = ref(null);
const chartInstance = ref(null);
const isLoading = ref(false);
const currentUserId = ref(null);

const scrollDepthPercentSeries = computed(() =>
  trendData.avg_scroll_depth.map((value) => Math.round(Number(value || 0) * 100))
);
const totalPv = computed(() => Number(trendData.total_pv || 0));
const totalUv = computed(() => Number(trendData.total_uv || 0));
const maxPv = computed(() => calculateMax(trendData.read_counts));
const maxUv = computed(() => calculateMax(trendData.uv_counts));
const maxDuration = computed(() => calculateMax(trendData.avg_read_duration));
const maxScrollDepth = computed(() => calculateMax(scrollDepthPercentSeries.value));
const latestPv = computed(() => getLastValue(trendData.read_counts));
const latestUv = computed(() => getLastValue(trendData.uv_counts));
const latestDuration = computed(() => getLastValue(trendData.avg_read_duration));
const latestScrollDepth = computed(() => getLastValue(scrollDepthPercentSeries.value));
const pvProgress = computed(() => calculateProgress(latestPv.value, maxPv.value));
const uvProgress = computed(() => calculateProgress(latestUv.value, maxUv.value));
const durationProgress = computed(() => calculateProgress(latestDuration.value, maxDuration.value));
const scrollDepthProgress = computed(() =>
  calculateProgress(latestScrollDepth.value, maxScrollDepth.value)
);

const avgDuration = computed(() => {
  const totalRead = trendData.read_counts.reduce((sum, value) => sum + (Number(value) || 0), 0);
  if (!trendData.avg_read_duration.length || !totalRead) return 0;
  const weightedTotal = trendData.avg_read_duration.reduce((sum, value, index) => {
    return sum + (Number(value) || 0) * (Number(trendData.read_counts[index]) || 0);
  }, 0);
  return Math.round(weightedTotal / totalRead);
});

const avgScrollDepth = computed(() => {
  if (!scrollDepthPercentSeries.value.length) return 0;
  const total = scrollDepthPercentSeries.value.reduce((sum, value) => sum + Number(value || 0), 0);
  return Math.round(total / scrollDepthPercentSeries.value.length);
});

function calculateMax(values) {
  if (!values || values.length === 0) return 0;
  return Math.max(...values.map((value) => Number(value) || 0));
}

function getLastValue(values) {
  if (!values || values.length === 0) return 0;
  return Number(values[values.length - 1]) || 0;
}

function calculateProgress(current, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((Number(current) / Number(max)) * 100));
}

function formatDuration(value) {
  const safeValue = Number(value || 0);
  if (!safeValue) return "--";
  const minutes = Math.round(safeValue / 60);
  return `${minutes} 分钟`;
}

function formatNumber(value) {
  const safeValue = Number(value) || 0;
  if (safeValue < 10000) {
    return `${safeValue}`;
  }
  return `${(safeValue / 10000).toFixed(1)}万`;
}

function formatDepth(value) {
  const safeValue = Number(value || 0);
  if (!safeValue) return "--";
  return `${safeValue}%`;
}

function initChart() {
  if (!chartRef.value || chartInstance.value) return;
  chartInstance.value = echarts.init(chartRef.value);
}

function updateChart() {
  if (!chartInstance.value) return;
  const pvGradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "#f97316" },
    { offset: 1, color: "#fed7aa" },
  ]);
  const durationGradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "rgba(59, 130, 246, 0.35)" },
    { offset: 1, color: "rgba(59, 130, 246, 0.05)" },
  ]);

  chartInstance.value.setOption({
    grid: { left: 40, right: 92, top: 46, bottom: 40 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { data: ["PV", "UV", "平均阅读时长", "平均滚动深度"] },
    xAxis: {
      type: "category",
      data: trendData.dates,
      axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.6)" } },
      axisLabel: { color: "#64748b" },
    },
    yAxis: [
      {
        type: "value",
        name: "PV/UV",
        axisLabel: { color: "#64748b" },
        splitLine: { lineStyle: { color: "rgba(226, 232, 240, 0.8)" } },
      },
      {
        type: "value",
        name: "时长(秒)",
        position: "right",
        axisLabel: { color: "#64748b" },
        splitLine: { show: false },
      },
      {
        type: "value",
        name: "深度(%)",
        position: "right",
        offset: 58,
        min: 0,
        max: 100,
        axisLabel: {
          color: "#64748b",
          formatter: "{value}%",
        },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "PV",
        type: "bar",
        data: trendData.read_counts,
        barMaxWidth: 24,
        itemStyle: {
          color: pvGradient,
          borderRadius: [8, 8, 0, 0],
        },
      },
      {
        name: "UV",
        type: "line",
        data: trendData.uv_counts,
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { color: "#0284c7", width: 2 },
        itemStyle: { color: "#0284c7" },
      },
      {
        name: "平均阅读时长",
        type: "line",
        yAxisIndex: 1,
        data: trendData.avg_read_duration,
        smooth: true,
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { color: "#3b82f6", width: 3 },
        itemStyle: { color: "#3b82f6" },
        areaStyle: { color: durationGradient },
      },
      {
        name: "平均滚动深度",
        type: "line",
        yAxisIndex: 2,
        data: scrollDepthPercentSeries.value,
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { color: "#0f766e", width: 2 },
        itemStyle: { color: "#0f766e" },
      },
    ],
    animationDuration: 800,
    animationEasing: "cubicOut",
  });
}

function resizeChart() {
  if (chartInstance.value) {
    chartInstance.value.resize();
  }
}

function disposeChart() {
  if (chartInstance.value) {
    chartInstance.value.dispose();
    chartInstance.value = null;
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

async function loadTrend() {
  if (!currentUserId.value) return;
  let hasError = false;
  try {
    disposeChart();
    isLoading.value = true;
    const data = await fetchReadTrend({
      user_id: currentUserId.value,
      start_date: filters.start_date,
      end_date: filters.end_date,
      granularity: filters.granularity,
    });
    trendData.dates = data?.dates || [];
    trendData.read_counts = data?.pv_counts || data?.read_counts || [];
    trendData.uv_counts = data?.uv_counts || [];
    trendData.total_pv = Number(data?.total_pv || 0);
    trendData.total_uv = Number(data?.total_uv || 0);
    trendData.avg_read_duration = data?.avg_read_duration || [];
    trendData.avg_scroll_depth = data?.avg_scroll_depth || [];
  } catch (_error) {
    hasError = true;
  } finally {
    isLoading.value = false;
  }

  if (hasError || trendData.dates.length === 0) return;
  await nextTick();
  initChart();
  updateChart();
}

async function handleMounted() {
  initChart();
  window.addEventListener("resize", resizeChart);
  await loadCurrentUser();
  await loadTrend();
}

onMounted(handleMounted);
onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
  disposeChart();
});
</script>
