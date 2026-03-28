<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">User Portrait</p>
      <h1 class="hero-title">用户画像分析</h1>
      <p class="hero-subtitle">兴趣标签、活跃时段热力图、行为分布与偏好分类。</p>
    </section>

    <AnalysisNav />

    <div v-if="isLoading" class="skeleton-list">
      <div v-for="item in 4" :key="item" class="skeleton-line"></div>
    </div>
    <EmptyState v-else-if="!currentUserId" title="需要登录" message="登录后可查看用户画像分析。" />
    <EmptyState
      v-else-if="isEmpty"
      title="暂无画像数据"
      message="请先产生阅读、搜索和互动行为。"
    />

    <div v-else class="analysis-grid">
      <SectionCard title="画像概览">
        <div class="portrait-kpi-grid">
          <div class="portrait-kpi portrait-kpi--warm">
            <p class="meta-text">平均阅读时长</p>
            <h3>{{ formatDuration(portraitData.avg_read_duration) }}</h3>
          </div>
          <div class="portrait-kpi">
            <p class="meta-text">行为类型数</p>
            <h3>{{ portraitData.behavior_distribution.length }}</h3>
          </div>
          <div class="portrait-kpi">
            <p class="meta-text">偏好分类数</p>
            <h3>{{ portraitData.preferred_categories.length }}</h3>
          </div>
          <div class="portrait-kpi portrait-kpi--cool">
            <p class="meta-text">搜索关键词数</p>
            <h3>{{ portraitData.recent_search_keywords.length }}</h3>
          </div>
          <div class="portrait-kpi">
            <p class="meta-text">平均滚动深度</p>
            <h3>{{ formatDepth(portraitData.avg_scroll_depth) }}</h3>
          </div>
          <div class="portrait-kpi">
            <p class="meta-text">最大滚动深度</p>
            <h3>{{ formatDepth(portraitData.max_scroll_depth) }}</h3>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="兴趣标签 Top 10">
        <div class="portrait-panel-grid">
          <div class="portrait-rank-list">
            <div
              v-for="(item, index) in portraitData.interest_tags_top10"
              :key="item.tag"
              class="portrait-rank-item"
            >
              <span class="portrait-rank-index">{{ index + 1 }}</span>
              <div class="portrait-rank-main">
                <div class="portrait-rank-line">
                  <span class="portrait-rank-label">{{ item.tag }}</span>
                  <span class="portrait-rank-value">{{ toPercent(item.weight) }}</span>
                </div>
                <div class="portrait-rank-bar">
                  <span
                    class="portrait-rank-fill"
                    :style="{ width: `${normalizeTagWeight(item.weight)}%` }"
                  ></span>
                </div>
              </div>
            </div>
          </div>
          <v-chart
            v-if="portraitData.interest_tags_top10.length >= 2"
            class="analysis-chart portrait-chart"
            :option="tagChartOption"
            autoresize
          />
        </div>
      </SectionCard>

      <SectionCard title="活跃时段热力图（7天 × 24小时）">
        <div v-if="peakActiveWindows.length" class="active-window-list">
          <div v-for="item in peakActiveWindows" :key="item.hour" class="active-window-item">
            <span>{{ formatHour(item.hour) }} - {{ formatHour((item.hour + 1) % 24) }}</span>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
        <div class="portrait-panel-grid">
          <v-chart class="analysis-chart portrait-chart portrait-chart--large" :option="heatmapOption" autoresize />
          <div class="portrait-rank-list">
            <div v-for="item in rankedActiveHours" :key="item.hour" class="portrait-rank-item">
              <span class="portrait-rank-index">{{ formatHour(item.hour) }}</span>
              <div class="portrait-rank-main">
                <div class="portrait-rank-line">
                  <span class="portrait-rank-label">活跃次数</span>
                  <span class="portrait-rank-value">{{ item.count }}</span>
                </div>
                <div class="portrait-rank-bar">
                  <span
                    class="portrait-rank-fill portrait-rank-fill--cool"
                    :style="{ width: `${normalizeHourCount(item.count)}%` }"
                  ></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="行为分布">
        <div class="portrait-rank-list">
          <div
            v-for="item in portraitData.behavior_distribution"
            :key="item.behavior_type"
            class="portrait-rank-item"
          >
            <span class="portrait-rank-index">{{ behaviorTypeLabel(item.behavior_type) }}</span>
            <div class="portrait-rank-main">
              <div class="portrait-rank-line">
                <span class="portrait-rank-label">次数</span>
                <span class="portrait-rank-value">{{ item.count }}</span>
              </div>
              <div class="portrait-rank-bar">
                <span
                  class="portrait-rank-fill portrait-rank-fill--ink"
                  :style="{ width: `${normalizeBehaviorCount(item.count)}%` }"
                ></span>
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="阅读深度分布">
        <div class="portrait-rank-list">
          <div
            v-for="item in portraitData.scroll_depth_distribution"
            :key="item.range"
            class="portrait-rank-item"
          >
            <span class="portrait-rank-index">{{ item.range }}</span>
            <div class="portrait-rank-main">
              <div class="portrait-rank-line">
                <span class="portrait-rank-label">次数</span>
                <span class="portrait-rank-value">{{ item.count }}</span>
              </div>
              <div class="portrait-rank-bar">
                <span
                  class="portrait-rank-fill portrait-rank-fill--ink"
                  :style="{ width: `${normalizeDepthCount(item.count)}%` }"
                ></span>
              </div>
            </div>
          </div>
          <EmptyState
            v-if="portraitData.scroll_depth_distribution.length === 0"
            title="暂无深度数据"
            message="阅读后会生成滚动深度统计。"
          />
        </div>
      </SectionCard>

      <SectionCard title="偏好分类与搜索词">
        <div class="portrait-double">
          <div class="portrait-subcard">
            <p class="portrait-subcard__title">偏好分类</p>
            <div class="portrait-rank-list">
              <div
                v-for="item in portraitData.preferred_categories"
                :key="item.category"
                class="portrait-rank-item"
              >
                <span class="portrait-rank-index">{{ item.category }}</span>
                <div class="portrait-rank-main">
                  <div class="portrait-rank-line">
                    <span class="portrait-rank-label">次数</span>
                    <span class="portrait-rank-value">{{ item.count }}</span>
                  </div>
                  <div class="portrait-rank-bar">
                    <span
                      class="portrait-rank-fill"
                      :style="{ width: `${normalizeCategoryCount(item.count)}%` }"
                    ></span>
                  </div>
                </div>
              </div>
              <EmptyState
                v-if="portraitData.preferred_categories.length === 0"
                title="暂无分类数据"
                message="还没有形成分类偏好。"
              />
            </div>
          </div>
          <div class="portrait-subcard">
            <p class="portrait-subcard__title">最近搜索关键词</p>
            <div class="portrait-rank-list">
              <div
                v-for="item in portraitData.recent_search_keywords"
                :key="item.keyword"
                class="portrait-rank-item"
              >
                <span class="portrait-rank-index">{{ item.keyword }}</span>
                <div class="portrait-rank-main">
                  <div class="portrait-rank-line">
                    <span class="portrait-rank-label">次数</span>
                    <span class="portrait-rank-value">{{ item.count }}</span>
                  </div>
                  <div class="portrait-rank-bar">
                    <span
                      class="portrait-rank-fill portrait-rank-fill--cool"
                      :style="{ width: `${normalizeKeywordCount(item.count)}%` }"
                    ></span>
                  </div>
                </div>
              </div>
              <EmptyState
                v-if="portraitData.recent_search_keywords.length === 0"
                title="暂无搜索数据"
                message="还没有记录搜索行为。"
              />
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { use } from "echarts/core";
import { BarChart, HeatmapChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, TooltipComponent, VisualMapComponent } from "echarts/components";
import VChart from "vue-echarts";
import AppLayout from "../../components/AppLayout.vue";
import AnalysisNav from "../../components/AnalysisNav.vue";
import SectionCard from "../../components/SectionCard.vue";
import EmptyState from "../../components/EmptyState.vue";
import { fetchActiveHeatmap, fetchUserPortrait } from "../../services/analysis.js";
import { fetchUserInfo } from "../../services/user.js";

use([CanvasRenderer, GridComponent, TooltipComponent, VisualMapComponent, BarChart, HeatmapChart]);

const portraitData = reactive({
  interest_tags_top10: [],
  behavior_distribution: [],
  preferred_categories: [],
  recent_search_keywords: [],
  avg_read_duration: 0,
  avg_scroll_depth: 0,
  max_scroll_depth: 0,
  scroll_depth_distribution: [],
});

const heatmapData = reactive({
  dates: [],
  hours: [],
  values: [],
  total_events: 0,
  peak_hours: [],
});

const isLoading = ref(false);
const currentUserId = ref(null);

const isEmpty = computed(() => {
  return (
    portraitData.interest_tags_top10.length === 0 &&
    portraitData.behavior_distribution.length === 0 &&
    portraitData.preferred_categories.length === 0 &&
    portraitData.recent_search_keywords.length === 0 &&
    portraitData.scroll_depth_distribution.length === 0 &&
    Number(heatmapData.total_events || 0) === 0
  );
});

const rankedActiveHours = computed(() => {
  if (heatmapData.peak_hours.length > 0) {
    return [...heatmapData.peak_hours]
      .map((item) => ({ hour: Number(item.hour || 0), count: Number(item.count || 0) }))
      .sort((a, b) => Number(b.count) - Number(a.count) || Number(a.hour) - Number(b.hour));
  }

  const counter = new Map();
  for (const row of heatmapData.values || []) {
    const hour = Number(row?.[1] || 0);
    const count = Number(row?.[2] || 0);
    counter.set(hour, (counter.get(hour) || 0) + count);
  }
  return Array.from(counter.entries())
    .map(([hour, count]) => ({ hour, count }))
    .sort((a, b) => Number(b.count) - Number(a.count) || Number(a.hour) - Number(b.hour))
    .slice(0, 10);
});

const peakActiveWindows = computed(() => rankedActiveHours.value.slice(0, 3));

const tagChartOption = computed(() => ({
  grid: { left: 34, right: 20, top: 24, bottom: 32 },
  tooltip: { trigger: "axis" },
  xAxis: {
    type: "category",
    data: portraitData.interest_tags_top10.map((item) => item.tag),
    axisLabel: { color: "#64748b", rotate: 20 },
    axisLine: { lineStyle: { color: "rgba(148,163,184,0.5)" } },
  },
  yAxis: {
    type: "value",
    axisLabel: { color: "#64748b" },
    splitLine: { lineStyle: { color: "rgba(226,232,240,0.9)" } },
  },
  series: [
    {
      type: "bar",
      data: portraitData.interest_tags_top10.map((item) => Number(item.weight || 0)),
      barMaxWidth: 28,
      itemStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "#f59e0b" },
            { offset: 1, color: "#fde68a" },
          ],
        },
        borderRadius: [8, 8, 0, 0],
      },
    },
  ],
  animationDuration: 700,
}));

const heatmapOption = computed(() => {
  const dateAxis = (heatmapData.dates || []).map((item) => String(item).slice(5));
  const hourAxis = (heatmapData.hours || []).map((hour) => formatHour(hour));
  const maxValue = Math.max(...(heatmapData.values || []).map((item) => Number(item?.[2] || 0)), 1);

  return {
    grid: { left: 64, right: 30, top: 20, bottom: 42 },
    tooltip: {
      position: "top",
      formatter(params) {
        const dateLabel = dateAxis[params.value[0]] || "";
        const hourLabel = hourAxis[params.value[1]] || "";
        return `${dateLabel} ${hourLabel}<br/>活跃次数: ${params.value[2]}`;
      },
    },
    xAxis: {
      type: "category",
      data: dateAxis,
      splitArea: { show: true },
      axisLabel: { color: "#64748b" },
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.5)" } },
    },
    yAxis: {
      type: "category",
      data: hourAxis,
      splitArea: { show: true },
      axisLabel: { color: "#64748b" },
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.5)" } },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      orient: "horizontal",
      left: "center",
      bottom: 2,
      inRange: {
        color: ["#f8fafc", "#dbeafe", "#93c5fd", "#3b82f6", "#1d4ed8"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: heatmapData.values || [],
        label: {
          show: false,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0, 0, 0, 0.25)",
          },
        },
      },
    ],
    animationDuration: 700,
  };
});

function maxOf(items, field) {
  if (!items.length) return 1;
  return Math.max(...items.map((item) => Number(item[field] || 0)), 1);
}

function normalize(value, max) {
  return Math.round((Number(value || 0) / Math.max(Number(max), 1)) * 100);
}

function normalizeTagWeight(weight) {
  return normalize(weight, maxOf(portraitData.interest_tags_top10, "weight"));
}

function normalizeHourCount(count) {
  return normalize(count, maxOf(rankedActiveHours.value, "count"));
}

function normalizeBehaviorCount(count) {
  return normalize(count, maxOf(portraitData.behavior_distribution, "count"));
}

function normalizeCategoryCount(count) {
  return normalize(count, maxOf(portraitData.preferred_categories, "count"));
}

function normalizeKeywordCount(count) {
  return normalize(count, maxOf(portraitData.recent_search_keywords, "count"));
}

function normalizeDepthCount(count) {
  return normalize(count, maxOf(portraitData.scroll_depth_distribution, "count"));
}

function behaviorTypeLabel(type) {
  const map = {
    read: "阅读",
    like: "点赞",
    collect: "收藏",
    comment: "评论",
    search: "搜索",
    page_view: "页面浏览",
    page_leave: "页面离开",
  };
  return map[String(type || "").toLowerCase()] || type || "未知行为";
}

function toPercent(weight) {
  return `${Math.round(Number(weight || 0) * 100)}%`;
}

function formatHour(hour) {
  return `${`${hour}`.padStart(2, "0")}:00`;
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (!value) return "--";
  if (value < 60) return `${value}秒`;
  return `${Math.round(value / 60)}分钟`;
}

function formatDepth(value) {
  const depth = Number(value || 0);
  return `${Math.round(depth * 100)}%`;
}

async function loadCurrentUser() {
  try {
    const data = await fetchUserInfo();
    currentUserId.value = data?.user_id || null;
  } catch (_error) {
    currentUserId.value = null;
  }
}

async function loadPortrait() {
  if (!currentUserId.value) return;
  try {
    isLoading.value = true;
    const [portrait, heatmap] = await Promise.all([
      fetchUserPortrait({ user_id: currentUserId.value }),
      fetchActiveHeatmap({ user_id: currentUserId.value, days: 7 }),
    ]);

    portraitData.interest_tags_top10 = portrait?.interest_tags_top10 || [];
    portraitData.behavior_distribution = portrait?.behavior_distribution || [];
    portraitData.preferred_categories = portrait?.preferred_categories || [];
    portraitData.recent_search_keywords = portrait?.recent_search_keywords || [];
    portraitData.avg_read_duration = Number(portrait?.avg_read_duration || 0);
    portraitData.avg_scroll_depth = Number(portrait?.avg_scroll_depth || 0);
    portraitData.max_scroll_depth = Number(portrait?.max_scroll_depth || 0);
    portraitData.scroll_depth_distribution = portrait?.scroll_depth_distribution || [];

    heatmapData.dates = heatmap?.dates || [];
    heatmapData.hours = heatmap?.hours || [];
    heatmapData.values = heatmap?.values || [];
    heatmapData.total_events = Number(heatmap?.total_events || 0);
    heatmapData.peak_hours = heatmap?.peak_hours || [];
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  await loadCurrentUser();
  await loadPortrait();
});
</script>

<style scoped>
.active-window-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.active-window-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(147, 197, 253, 0.8);
  background: rgba(239, 246, 255, 0.8);
  color: #1e3a8a;
  font-size: 0.8rem;
}
</style>
