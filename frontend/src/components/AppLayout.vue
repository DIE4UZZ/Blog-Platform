<template>
  <div class="page-shell">
    <header class="top-nav">
      <div class="brand">
        <span class="brand-dot"></span>
        <span>Blog Platform</span>
      </div>
      <nav class="nav-links">
        <router-link class="nav-link" to="/">推荐</router-link>
        <router-link class="nav-link" to="/rank">排行榜</router-link>
        <router-link class="nav-link" to="/articles">文章</router-link>
        <router-link class="nav-link" to="/editor">创作</router-link>
        <router-link class="nav-link" to="/profile">个人中心</router-link>
        <router-link class="nav-link" to="/analysis">数据分析</router-link>
        <router-link v-if="isAdmin" class="nav-link" to="/admin">管理后台</router-link>
      </nav>
      <div class="nav-actions">
        <template v-if="!isLoggedIn">
          <router-link class="ghost-button" to="/login">登录</router-link>
          <router-link class="solid-button" to="/register">注册</router-link>
        </template>
        <template v-else>
          <span class="meta-text">{{ displayName }}</span>
          <el-button class="ghost-button" @click="handleLogout">退出登录</el-button>
        </template>
      </div>
    </header>

    <main class="page-container">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearAuthToken, getAuthToken } from "../services/http.js";
import { clearCachedUserInfo, getCachedUserInfo } from "../services/user.js";

const router = useRouter();
const route = useRoute();
const userInfo = ref(getCachedUserInfo());

const isLoggedIn = computed(() => Boolean(getAuthToken()));
const isAdmin = computed(() => userInfo.value?.role === "admin");
const displayName = computed(() => userInfo.value?.username || userInfo.value?.email || "用户");

watch(
  () => route.fullPath,
  () => {
    userInfo.value = getCachedUserInfo();
  },
  { immediate: true }
);

function handleLogout() {
  clearAuthToken();
  clearCachedUserInfo();
  userInfo.value = null;
  router.push("/login");
}
</script>
