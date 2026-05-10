/**
 * router/index.js —— 前端路由配置模块
 *
 * 使用 Vue Router 4 配置单页应用的路由规则，包含：
 *   1. 路由表定义（路径 → 组件映射）
 *   2. 路由守卫（beforeEach）：登录认证 + 管理员权限校验
 *   3. 路由后置钩子（afterEach）：上报页面访问行为（用于数据分析）
 *
 * 路由 meta 字段说明：
 *   - transition: 页面切换动画名称（在 App.vue 中使用）
 *   - requiresAuth: true → 需要登录才能访问，未登录跳转 /login
 *   - requiresAdmin: true → 需要管理员角色，非管理员跳转首页
 */

import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import LeaderboardView from "../views/LeaderboardView.vue";
import ArticlesView from "../views/ArticlesView.vue";
import ArticleDetailView from "../views/ArticleDetailView.vue";
import EditorView from "../views/EditorView.vue";
import ProfileView from "../views/ProfileView.vue";
import AnalysisView from "../views/AnalysisView.vue";
import FollowingFeedView from "../views/FollowingFeedView.vue";
import NotificationsView from "../views/NotificationsView.vue";
import ReadTrendView from "../views/analysis/ReadTrendView.vue";
import RecommendEffectView from "../views/analysis/RecommendEffectView.vue";
import UserPortraitView from "../views/analysis/UserPortraitView.vue";
import ContentPerformanceView from "../views/analysis/ContentPerformanceView.vue";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";
import AdminView from "../views/AdminView.vue";
import { getAuthToken } from "../services/http.js";
import { getCachedUserInfo } from "../services/user.js";
import { reportBehavior } from "../services/behavior.js";

/**
 * 创建并配置 Vue Router 实例。
 *
 * 使用 HTML5 History 模式（createWebHistory），URL 无 # 号。
 * 路由表按功能分组：
 *   - 公开页面：首页、排行榜、文章列表、文章详情、登录、注册
 *   - 需要登录：编辑器、个人中心、关注动态、通知、数据分析
 *   - 需要管理员：后台管理
 *
 * @returns {import("vue-router").Router} Vue Router 实例。
 */
function createAppRouter() {
  return createRouter({
    history: createWebHistory(),  // HTML5 History 模式（无 # 号）
    routes: [
      // ===== 公开页面（无需登录）=====
      { path: "/", name: "home", component: HomeView, meta: { transition: "fade" } },
      { path: "/rank", name: "rank", component: LeaderboardView, meta: { transition: "fade" } },
      { path: "/articles", name: "articles", component: ArticlesView, meta: { transition: "slide-left" } },
      {
        path: "/articles/:id",          // 文章详情页，:id 为文章 ID
        name: "article-detail",
        component: ArticleDetailView,
        meta: { transition: "slide-left" },
      },

      // ===== 需要登录的页面（requiresAuth: true）=====
      {
        path: "/editor",                // 新建文章
        name: "editor",
        component: EditorView,
        meta: { transition: "scale-fade", requiresAuth: true },
      },
      {
        path: "/editor/:id",            // 编辑已有文章，:id 为文章 ID
        name: "editor-edit",
        component: EditorView,
        meta: { transition: "scale-fade", requiresAuth: true },
      },
      {
        path: "/profile",               // 个人中心
        name: "profile",
        component: ProfileView,
        meta: { transition: "slide-right", requiresAuth: true },
      },
      {
        path: "/following",             // 关注动态流
        name: "following",
        component: FollowingFeedView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/notifications",         // 通知中心
        name: "notifications",
        component: NotificationsView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis",              // 数据分析总览
        name: "analysis",
        component: AnalysisView,
        meta: { transition: "fade", requiresAuth: true },
      },
      {
        path: "/analysis/read-trend",   // 阅读趋势分析
        name: "analysis-read-trend",
        component: ReadTrendView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/recommend-effect",  // 推荐效果分析
        name: "analysis-recommend-effect",
        component: RecommendEffectView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/user-portrait",     // 用户画像分析
        name: "analysis-user-portrait",
        component: UserPortraitView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/content-performance",  // 内容表现分析
        name: "analysis-content-performance",
        component: ContentPerformanceView,
        meta: { transition: "slide-left", requiresAuth: true },
      },

      // ===== 需要管理员权限的页面（requiresAdmin: true）=====
      {
        path: "/admin",                 // 后台管理
        name: "admin",
        component: AdminView,
        meta: { transition: "fade", requiresAuth: true, requiresAdmin: true },
      },

      // ===== 认证页面（已登录时重定向到首页）=====
      { path: "/login", name: "login", component: LoginView },
      { path: "/register", name: "register", component: RegisterView },

      // ===== 404 兜底：未匹配的路径重定向到首页 =====
      { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
  });
}

// 创建全局路由实例
const router = createAppRouter();

/**
 * 全局前置路由守卫（导航前执行）。
 *
 * 校验逻辑：
 *   1. requiresAuth=true 且未登录 → 跳转 /login（携带 redirect 参数，登录后可回跳）
 *   2. requiresAdmin=true 且非管理员 → 跳转首页
 *   3. 已登录时访问 /login 或 /register → 跳转首页（防止重复登录）
 *   4. 其他情况 → 正常导航（return true）
 */
router.beforeEach((to) => {
  const token = getAuthToken();           // 从 localStorage 读取 JWT Token
  const userInfo = getCachedUserInfo();   // 从 localStorage 读取缓存的用户信息

  // 需要登录但未登录：跳转到登录页，并携带 redirect 参数
  if (to.meta?.requiresAuth && !token) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  // 需要管理员权限但非管理员：跳转首页
  if (to.meta?.requiresAdmin && userInfo?.role !== "admin") {
    return "/";
  }
  // 已登录时访问登录/注册页：跳转首页
  if ((to.path === "/login" || to.path === "/register") && token) {
    return "/";
  }
  return true;  // 正常导航
});

/**
 * 全局后置路由钩子（导航完成后执行）。
 *
 * 用于上报用户行为数据（页面访问和离开），供后端数据分析使用：
 *   - page_leave：记录用户离开的页面路径
 *   - page_view：记录用户访问的页面路径
 *
 * 注意：reportBehavior 内部会忽略未登录用户的上报（静默失败）。
 */
router.afterEach((to, from) => {
  // 上报离开行为（from.fullPath 存在时才上报，避免首次加载时上报空路径）
  if (from?.fullPath) {
    reportBehavior({
      behavior_type: "page_leave",
      keyword: from.fullPath,   // 用 keyword 字段存储页面路径
    });
  }
  // 上报访问行为
  reportBehavior({
    behavior_type: "page_view",
    keyword: to.fullPath,
  });
});

export default router;
