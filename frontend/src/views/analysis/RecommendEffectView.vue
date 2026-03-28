<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">推荐效果</p>
      <h1 class="hero-title">推荐效果分析</h1>
      <p class="hero-subtitle">支持趋势对比、基准线观察与阶段变化判断。</p>
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
        <button type="button" class="solid-button analysis-button" :disabled="isLoading" @click="loadEffect">
          刷新数据
        </button>
      </div>
    </SectionCard>

    <div v-if="isLoading" class="skeleton-list">
      <div v-for="item in 3" :key="item" class="skeleton-line"></div>
    </div>
    <EmptyState
      v-else-if="!currentUserId"
      title="需要登录"
      message="登录后即可查看推荐效果分析。"
    />

    <div v-else class="analysis-grid">
      <SectionCard title="关键指标">
        <div class="metric-grid metric-grid--wide">
          <div class="metric-card">
            <p class="meta-text">推荐点击率</p>
            <h3 class="metric-value">{{ formatPercent(effectData.click_through_rate) }}</h3>
            <p class="metric-delta" :class="deltaClass(comparison.click_through_rate_change)">
              较上期 {{ formatSignedPercent(comparison.click_through_rate_change) }}
            </p>
          </div>
          <div class="metric-card">
            <p class="meta-text">推荐转化率</p>
            <h3 class="metric-value">{{ formatPercent(effectData.conversion_rate) }}</h3>
            <p class="metric-delta" :class="deltaClass(comparison.conversion_rate_change)">
              较上期 {{ formatSignedPercent(comparison.conversion_rate_change) }}
            </p>
          </div>
          <div class="metric-card">
            <p class="meta-text">曝光量</p>
            <h3 class="metric-value">{{ formatCount(totalImpressions) }}</h3>
            <p class="meta-text">点击 {{ formatCount(totalClicks) }}</p>
          </div>
          <div class="metric-card">
            <p class="meta-text">转化量</p>
            <h3 class="metric-value">{{ formatCount(totalConversions) }}</h3>
            <p class="meta-text">最佳 CTR 日 {{ comparison.best_ctr_date || "--" }}</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="趋势对比">
        <div class="trend-summary">
          <span class="tag-chip">CTR 日均 {{ formatPercent(comparison.average_daily_ctr) }}</span>
          <span class="tag-chip">转化率日均 {{ formatPercent(comparison.average_daily_conversion) }}</span>
        </div>
        <p v-if="!hasDaily" class="meta-text">当前时间范围暂无曝光数据，已展示零值趋势图。</p>
        <v-chart class="analysis-chart" :option="chartOption" autoresize />
      </SectionCard>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { use } from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import VChart from "vue-echarts";
import AppLayout from "../../components/AppLayout.vue";
import AnalysisNav from "../../components/AnalysisNav.vue";
import SectionCard from "../../components/SectionCard.vue";
import EmptyState from "../../components/EmptyState.vue";
import { fetchRecommendEffect } from "../../services/analysis.js";
import { fetchUserInfo } from "../../services/user.js";
import { createDefaultRange, formatPercent } from "../../utils/analysis.js";

use([CanvasRenderer, GridComponent, TooltipComponent, LegendComponent, BarChart, LineChart]);

const defaultRange = createDefaultRange(14);
const filters = reactive({
  start_date: defaultRange.start,
  end_date: defaultRange.end,
});
const effectData = reactive({
  click_through_rate: 0,
  conversion_rate: 0,
  impressions: 0,
  clicks: 0,
  conversions: 0,
  daily: [],
  comparison: {},
});
const isLoading = ref(false);
const currentUserId = ref(null);

const hasDaily = computed(() => effectData.daily.length > 0);
const comparison = computed(() => effectData.comparison || {});
const totalImpressions = computed(() => {
  if (Number(effectData.impressions) > 0) return Number(effectData.impressions);
  return effectData.daily.reduce((sum, item) => sum + Number(item.impressions || 0), 0);
});
const totalClicks = computed(() => {
  if (Number(effectData.clicks) > 0) return Number(effectData.clicks);
  return effectData.daily.reduce((sum, item) => sum + Number(item.clicks || 0), 0);
});
const totalConversions = computed(() => {
  if (Number(effectData.conversions) > 0) return Number(effectData.conversions);
  return effectData.daily.reduce((sum, item) => sum + Number(item.conversions || 0), 0);
});

function parseDate(dateText) {
  const [year, month, day] = String(dateText).split("-").map((item) => Number(item));
  return new Date(year, (month || 1) - 1, day || 1);
}

function toDateText(dateObj) {
  const year = dateObj.getFullYear();
  const month = `${dateObj.getMonth() + 1}`.padStart(2, "0");
  const day = `${dateObj.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildFallbackDaily(startDate, endDate) {
  const rows = [];
  const start = parseDate(startDate);
  const end = parseDate(endDate);
  const totalDays = Math.max(1, Math.min(31, Math.ceil((end - start) / 86400000) + 1));
  for (let index = 0; index < totalDays; index += 1) {
    const current = new Date(start.getTime());
    current.setDate(start.getDate() + index);
    rows.push({
      date: toDateText(current),
      impressions: 0,
      clicks: 0,
      conversions: 0,
      ctr: 0,
      conversion: 0,
    });
  }
  return rows;
}

function toPercentText(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

const dailyRowsForChart = computed(() => {
  return hasDaily.value
    ? effectData.daily
    : buildFallbackDaily(filters.start_date, filters.end_date);
});

const chartOption = computed(() => {
  const dates = dailyRowsForChart.value.map((item) => item.date);
  const impressionValues = dailyRowsForChart.value.map((item) => Number(item.impressions || 0));
  const ctrValues = dailyRowsForChart.value.map((item) => Number(item.ctr || 0));
  const conversionValues = dailyRowsForChart.value.map((item) => Number(item.conversion || 0));
  const avgCtr = Number(comparison.value.average_daily_ctr || 0);
  const avgConversion = Number(comparison.value.average_daily_conversion || 0);

  return {
    grid: { left: 44, right: 44, top: 52, bottom: 40 },
    legend: { data: ["曝光量", "点击率", "转化率", "点击率均值", "转化率均值"] },
    tooltip: {
      trigger: "axis",
      formatter(params) {
        const lines = params.map((item) => {
          const isRate = ["点击率", "转化率", "点击率均值", "转化率均值"].includes(item.seriesName);
          const valueText = isRate ? toPercentText(item.value) : `${Number(item.value || 0)}`;
          return `${item.marker}${item.seriesName}: ${valueText}`;
        });
        return [`<strong>${params[0]?.axisValue || ""}</strong>`, ...lines].join("<br/>");
      },
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.6)" } },
      axisLabel: { color: "#64748b" },
    },
    yAxis: [
      {
        type: "value",
        name: "曝光量",
        axisLabel: { color: "#64748b" },
        splitLine: { lineStyle: { color: "rgba(226,232,240,0.85)" } },
      },
      {
        type: "value",
        name: "比率",
        min: 0,
        max: 1,
        axisLabel: {
          color: "#64748b",
          formatter: (value) => `${Math.round(Number(value) * 100)}%`,
        },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "曝光量",
        type: "bar",
        yAxisIndex: 0,
        barMaxWidth: 26,
        data: impressionValues,
        itemStyle: { color: "rgba(148,163,184,0.75)", borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "点击率",
        type: "line",
        yAxisIndex: 1,
        data: ctrValues,
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { width: 3, color: "#2563eb" },
        itemStyle: { color: "#1d4ed8" },
      },
      {
        name: "转化率",
        type: "line",
        yAxisIndex: 1,
        data: conversionValues,
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { width: 3, color: "#f59e0b" },
        itemStyle: { color: "#d97706" },
      },
      {
        name: "点击率均值",
        type: "line",
        yAxisIndex: 1,
        data: dates.map(() => avgCtr),
        symbol: "none",
        lineStyle: { width: 2, type: "dashed", color: "rgba(37,99,235,0.45)" },
        emphasis: { disabled: true },
      },
      {
        name: "转化率均值",
        type: "line",
        yAxisIndex: 1,
        data: dates.map(() => avgConversion),
        symbol: "none",
        lineStyle: { width: 2, type: "dashed", color: "rgba(245,158,11,0.5)" },
        emphasis: { disabled: true },
      },
    ],
    animationDuration: 750,
  };
});

function formatCount(value) {
  return `${Number(value || 0)}`;
}

function formatSignedPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  const rate = Number(value) * 100;
  const sign = rate > 0 ? "+" : "";
  return `${sign}${rate.toFixed(1)}%`;
}

function deltaClass(value) {
  if (typeof value !== "number" || Number.isNaN(value) || value === 0) {
    return "metric-delta--flat";
  }
  return value > 0 ? "metric-delta--up" : "metric-delta--down";
}

async function loadCurrentUser() {
  try {
    const data = await fetchUserInfo();
    currentUserId.value = data?.user_id || null;
  } catch (_error) {
    currentUserId.value = null;
  }
}

async function loadEffect() {
  if (!currentUserId.value) return;
  try {
    isLoading.value = true;
    const data = await fetchRecommendEffect({
      user_id: currentUserId.value,
      start_date: filters.start_date,
      end_date: filters.end_date,
    });
    effectData.click_through_rate = Number(data?.click_through_rate || 0);
    effectData.conversion_rate = Number(data?.conversion_rate || 0);
    effectData.impressions = Number(data?.impressions || 0);
    effectData.clicks = Number(data?.clicks || 0);
    effectData.conversions = Number(data?.conversions || 0);
    effectData.daily = (data?.daily || []).map((item) => ({
      date: item.date,
      impressions: Number(item.impressions || 0),
      clicks: Number(item.clicks || 0),
      conversions: Number(item.conversions || 0),
      ctr: Number(item.ctr || 0),
      conversion: Number(item.conversion || 0),
    }));
    effectData.comparison = data?.comparison || {};
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  await loadCurrentUser();
  await loadEffect();
});
</script>

<style scoped>
.metric-grid--wide {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.metric-delta {
  margin: 8px 0 0;
  font-size: 0.82rem;
}

.metric-delta--up {
  color: #059669;
}

.metric-delta--down {
  color: #dc2626;
}

.metric-delta--flat {
  color: #64748b;
}

.trend-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
