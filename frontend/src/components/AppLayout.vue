<template>
  <div class="page-shell">
    <header class="top-nav">
      <div class="top-nav__inner">
        <!-- 左侧：品牌 Logo -->
        <router-link class="brand" to="/">
          <span class="brand-mark">
            <span class="brand-dot"></span>
          </span>
          <span class="brand-name">Blog Platform</span>
        </router-link>

        <!-- 中间：核心导航链接 -->
        <nav class="nav-links">
          <router-link class="nav-link" to="/">推荐</router-link>
          <router-link class="nav-link" to="/following">关注</router-link>
          <router-link class="nav-link" to="/rank">排行榜</router-link>
          <router-link class="nav-link" to="/articles">文章</router-link>
          <router-link class="nav-link" to="/analysis">数据分析</router-link>
          <router-link v-if="isAdmin" class="nav-link" to="/admin">管理后台</router-link>
        </nav>

        <!-- 右侧：图标操作组 -->
        <div class="nav-actions">
          <template v-if="!isLoggedIn">
            <router-link class="ghost-button ghost-button--compact" to="/login">登录</router-link>
            <router-link class="solid-button solid-button--compact" to="/register">注册</router-link>
          </template>
          <template v-else>
            <!-- 写文章按钮 -->
            <router-link class="nav-icon-btn nav-icon-btn--write" to="/editor" title="写文章">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 20h9"/>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
              <span class="nav-icon-btn__label">创作</span>
            </router-link>

            <!-- 通知按钮 -->
            <router-link class="nav-icon-btn" to="/notifications" title="通知">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
              <span v-if="unreadNotificationCount > 0" class="nav-icon-btn__badge">{{ unreadNotificationCount > 99 ? '99+' : unreadNotificationCount }}</span>
            </router-link>

            <!-- 个人中心按钮 -->
            <router-link class="nav-icon-btn" to="/profile" title="个人中心">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </router-link>

            <!-- 用户名 + 退出 -->
            <div class="user-chip" @click="showUserMenu = !showUserMenu">
              <span class="user-chip__name">{{ displayName }}</span>
              <svg class="user-chip__arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
              <div v-if="showUserMenu" class="user-dropdown">
                <button class="user-dropdown__item" @click.stop="handleLogout">退出登录</button>
              </div>
            </div>
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
const showUserMenu = ref(false);

const isLoggedIn = computed(() => Boolean(getAuthToken()));
const isAdmin = computed(() => userInfo.value?.role === "admin");
const displayName = computed(() => userInfo.value?.username || userInfo.value?.email || "用户");
const unreadNotificationCount = computed(() => Number(userInfo.value?.unread_notification_count || 0));

watch(
  () => route.fullPath,
  () => {
    userInfo.value = getCachedUserInfo();
    showUserMenu.value = false;
  },
  { immediate: true }
);

window.addEventListener("blog-user-info-updated", () => {
  userInfo.value = getCachedUserInfo();
});

// 点击外部关闭下拉菜单
window.addEventListener("click", (e) => {
  if (!e.target.closest(".user-chip")) {
    showUserMenu.value = false;
  }
});

function handleLogout() {
  clearAuthToken();
  clearCachedUserInfo();
  userInfo.value = null;
  showUserMenu.value = false;
  router.push("/login");
}
</script>

<style scoped>
/* ===== 导航栏图标按钮 ===== */
.nav-icon-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  color: var(--ink-soft);
  text-decoration: none;
  transition: all 0.2s ease;
  background: transparent;
}

.nav-icon-btn:hover {
  color: var(--ink-strong);
  background: rgba(20, 33, 50, 0.06);
}

.nav-icon-btn.router-link-active {
  color: var(--accent);
  background: rgba(23, 98, 79, 0.08);
}

.nav-icon-btn--write {
  width: auto;
  padding: 0 14px;
  gap: 6px;
  border-radius: 999px;
  background: linear-gradient(135deg, #153d32, #1e5b49);
  color: #ffffff;
  font-weight: 600;
  font-size: 0.82rem;
}

.nav-icon-btn--write:hover {
  color: #ffffff;
  background: linear-gradient(135deg, #174839, #22624f);
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(21, 61, 50, 0.2);
}

.nav-icon-btn__label {
  font-size: 0.82rem;
  font-weight: 600;
}

.nav-icon-btn__badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #ef4444;
  color: #ffffff;
  font-size: 0.62rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* ===== 用户下拉菜单 ===== */
.user-chip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(20, 33, 50, 0.05);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.user-chip:hover {
  background: rgba(20, 33, 50, 0.09);
}

.user-chip__name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink-strong);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chip__arrow {
  color: var(--ink-soft);
  transition: transform 0.2s ease;
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 120px;
  padding: 6px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(20, 33, 50, 0.08);
  box-shadow: 0 12px 32px rgba(20, 33, 50, 0.12);
  backdrop-filter: blur(12px);
  z-index: 100;
}

.user-dropdown__item {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--ink-strong);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}

.user-dropdown__item:hover {
  background: rgba(20, 33, 50, 0.06);
}
</style>
