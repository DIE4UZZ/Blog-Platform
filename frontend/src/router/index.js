import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";

/**
 * Build the application router.
 * @returns {import("vue-router").Router} Vue Router instance.
 */
function createAppRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/", redirect: "/login" },
      { path: "/login", name: "login", component: LoginView },
      { path: "/register", name: "register", component: RegisterView },
    ],
  });
}

const router = createAppRouter();

export default router;
