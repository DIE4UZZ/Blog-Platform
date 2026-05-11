<!--
  App.vue —— 应用根组件

  职责：
    1. 提供全局背景装饰层（aurora 光晕效果）
    2. 承载 <router-view>，渲染当前路由对应的页面组件
    3. 使用 Vue Transition 实现页面切换的淡入淡出动画

  注意事项：
    - 不使用 mode="out-in"，避免复杂组件树下 transition 卡住导致白屏
    - 使用简单的 fade 动画，确保兼容性
-->
<template>
  <div class="app-shell">
    <!-- 背景装饰层：两个渐变光晕球，纯视觉效果 -->
    <div class="aurora-layer" aria-hidden="true">
      <span class="orb orb-one"></span>
      <span class="orb orb-two"></span>
    </div>
    <!-- 路由视图：直接渲染当前路由组件，不使用 transition 动画 -->
    <!-- 移除 transition 包裹以彻底避免 out-in 模式下的白屏问题 -->
    <router-view />
  </div>
</template>

<script setup>
/**
 * App.vue 根组件
 *
 * 作为 Vue 应用的最外层容器，不包含业务逻辑。
 * 所有页面级逻辑（导航、认证等）由 AppLayout 组件和路由守卫处理。
 */
</script>
