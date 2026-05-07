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
 * Build the application router.
 * @returns {import("vue-router").Router} Vue Router instance.
 */
function createAppRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/", name: "home", component: HomeView, meta: { transition: "fade" } },
      { path: "/rank", name: "rank", component: LeaderboardView, meta: { transition: "fade" } },
      { path: "/articles", name: "articles", component: ArticlesView, meta: { transition: "slide-left" } },
      {
        path: "/articles/:id",
        name: "article-detail",
        component: ArticleDetailView,
        meta: { transition: "slide-left" },
      },
      {
        path: "/editor",
        name: "editor",
        component: EditorView,
        meta: { transition: "scale-fade", requiresAuth: true },
      },
      {
        path: "/editor/:id",
        name: "editor-edit",
        component: EditorView,
        meta: { transition: "scale-fade", requiresAuth: true },
      },
      {
        path: "/profile",
        name: "profile",
        component: ProfileView,
        meta: { transition: "slide-right", requiresAuth: true },
      },
      {
        path: "/following",
        name: "following",
        component: FollowingFeedView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/notifications",
        name: "notifications",
        component: NotificationsView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis",
        name: "analysis",
        component: AnalysisView,
        meta: { transition: "fade", requiresAuth: true },
      },
      {
        path: "/analysis/read-trend",
        name: "analysis-read-trend",
        component: ReadTrendView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/recommend-effect",
        name: "analysis-recommend-effect",
        component: RecommendEffectView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/user-portrait",
        name: "analysis-user-portrait",
        component: UserPortraitView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/analysis/content-performance",
        name: "analysis-content-performance",
        component: ContentPerformanceView,
        meta: { transition: "slide-left", requiresAuth: true },
      },
      {
        path: "/admin",
        name: "admin",
        component: AdminView,
        meta: { transition: "fade", requiresAuth: true, requiresAdmin: true },
      },
      { path: "/login", name: "login", component: LoginView },
      { path: "/register", name: "register", component: RegisterView },
      { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
  });
}

const router = createAppRouter();

router.beforeEach((to) => {
  const token = getAuthToken();
  const userInfo = getCachedUserInfo();
  if (to.meta?.requiresAuth && !token) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  if (to.meta?.requiresAdmin && userInfo?.role !== "admin") {
    return "/";
  }
  if ((to.path === "/login" || to.path === "/register") && token) {
    return "/";
  }
  return true;
});

router.afterEach((to, from) => {
  if (from?.fullPath) {
    reportBehavior({
      behavior_type: "page_leave",
      keyword: from.fullPath,
    });
  }
  reportBehavior({
    behavior_type: "page_view",
    keyword: to.fullPath,
  });
});

export default router;
