<template>
  <section class="section-card">
    <header v-if="title" class="section-card__header">
      <h3 class="section-card__title">{{ title }}</h3>
      <slot name="actions" />
    </header>
    <div class="section-card__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: "",
  },
});
</script>
