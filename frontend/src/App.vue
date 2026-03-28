<template>
  <div class="app-shell">
    <div class="aurora-layer" aria-hidden="true">
      <span class="orb orb-one"></span>
      <span class="orb orb-two"></span>
    </div>
    <router-view v-slot="{ Component, route }">
      <transition :name="route.meta?.transition || 'fade'" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </transition>
    </router-view>
  </div>
</template>
