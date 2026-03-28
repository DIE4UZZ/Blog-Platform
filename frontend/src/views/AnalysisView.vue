<template>
  <AppLayout>
    <section class="hero-block hero-compact">
      <p class="hero-kicker">Analytics</p>
      <h1 class="hero-title">数据洞察</h1>
      <p class="hero-subtitle">
        以清晰的指标视角，追踪阅读、推荐、用户画像与内容表现的关键变化。
      </p>
    </section>

    <AnalysisNav />

    <div class="analysis-grid analysis-grid--cards">
      <SectionCard title="阅读趋势分析">
        <p class="analysis-card__description">
          按日/周/月统计阅读量与平均阅读时长，观察内容消费节奏与峰值变化。
        </p>
        <router-link class="text-link" to="/analysis/read-trend">进入趋势分析</router-link>
      </SectionCard>

      <SectionCard title="推荐效果分析">
        <p class="analysis-card__description">
          跟踪推荐点击率与转化率，评估推荐策略与素材组合的效果。
        </p>
        <router-link class="text-link" to="/analysis/recommend-effect">进入效果分析</router-link>
      </SectionCard>

      <SectionCard title="用户画像分析">
        <p class="analysis-card__description">
          展示用户兴趣标签 TOP10 与活跃时段，支撑个性化推荐与冷启动策略。
        </p>
        <router-link class="text-link" to="/analysis/user-portrait">进入画像分析</router-link>
      </SectionCard>

      <SectionCard title="内容表现分析">
        <p class="analysis-card__description">
          对文章阅读量排行与互动率排行进行对比，帮助找出优质内容方向。
        </p>
        <router-link class="text-link" to="/analysis/content-performance">进入表现分析</router-link>
      </SectionCard>
    </div>
  </AppLayout>
</template>

<script setup>
import AppLayout from "../components/AppLayout.vue";
import AnalysisNav from "../components/AnalysisNav.vue";
import SectionCard from "../components/SectionCard.vue";
</script>
