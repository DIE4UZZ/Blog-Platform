<template>
  <div class="page-shell">
    <header class="top-nav">
      <div class="top-nav__inner">
        <div class="brand-cluster">
          <router-link class="brand" to="/">
            <span class="brand-mark">
              <span class="brand-dot"></span>
            </span>
            <span class="brand-copy">
              <span class="brand-name">Blog Platform</span>
              <span class="brand-note">智能推荐与创作者分析</span>
            </span>
          </router-link>
          <span class="brand-badge">Responsive</span>
        </div>

        <nav class="nav-links">
          <router-link class="nav-link" to="/">推荐</router-link>
          <router-link class="nav-link" to="/rank">排行榜</router-link>
          <router-link class="nav-link" to="/articles">文章</router-link>
          <router-link class="nav-link" to="/editor">创作</router-link>
          <router-link class="nav-link" to="/profile">个人中心</router-link>
          <router-link v-if="isLoggedIn" class="nav-link" to="/following">关注流</router-link>
          <router-link v-if="isLoggedIn" class="nav-link" to="/notifications">
            通知<span v-if="unreadNotificationCount > 0"> ({{ unreadNotificationCount }})</span>
          </router-link>
          <router-link class="nav-link" to="/analysis">数据分析</router-link>
          <router-link v-if="isAdmin" class="nav-link" to="/admin">管理后台</router-link>
        </nav>

        <div class="nav-actions">
          <template v-if="!isLoggedIn">
            <router-link class="ghost-button" to="/login">登录</router-link>
            <router-link class="solid-button" to="/register">立即注册</router-link>
          </template>
          <template v-else>
            <div class="user-chip">
              <span class="user-chip__label">当前账号</span>
              <span class="user-chip__name">{{ displayName }}</span>
            </div>
            <router-link class="solid-button solid-button--compact" to="/editor">写文章</router-link>
            <el-button class="ghost-button" @click="handleLogout">退出登录</el-button>
          </template>
        </div>
      </div>
    </header>

    <main class="page-container">
      <slot />
    </main>

    <footer class="page-footer">
      <p class="page-footer__title">融合推荐、写作与数据洞察的一体化博客平台</p>
      <div class="page-footer__links">
        <router-link class="text-link" to="/articles">内容浏览</router-link>
        <router-link class="text-link" to="/editor">开始创作</router-link>
        <router-link class="text-link" to="/analysis">查看分析</router-link>
      </div>
    </footer>
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
const unreadNotificationCount = computed(() => Number(userInfo.value?.unread_notification_count || 0));

watch(
  () => route.fullPath,
  () => {
    userInfo.value = getCachedUserInfo();
  },
  { immediate: true }
);

window.addEventListener("blog-user-info-updated", () => {
  userInfo.value = getCachedUserInfo();
});

function handleLogout() {
  clearAuthToken();
  clearCachedUserInfo();
  userInfo.value = null;
  router.push("/login");
}
</script>
