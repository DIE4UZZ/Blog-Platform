<template>
  <div class="empty-state">
    <span class="empty-state__icon" aria-hidden="true"></span>
    <p class="empty-state__title">{{ title }}</p>
    <p class="empty-state__message">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: "暂无数据",
  },
  message: {
    type: String,
    default: "稍后再试或调整筛选条件。",
  },
});
</script>
