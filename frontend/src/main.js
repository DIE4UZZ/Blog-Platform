/**
 * main.js —— Vue 应用入口文件
 *
 * 负责创建并挂载 Vue 应用实例，注册全局插件：
 *   - Vue Router：单页路由（router/index.js）
 *   - Element Plus：UI 组件库（含全局样式）
 *
 * 挂载点：index.html 中的 <div id="app">
 */

import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";   // Element Plus 全局样式
import App from "./App.vue";
import router from "./router/index.js";
import "./index.css";                   // 项目全局样式（Tailwind CSS）

/**
 * 初始化并挂载 Vue 应用。
 *
 * 使用函数封装而非直接调用，便于测试和扩展（如 SSR 场景）。
 * 注册顺序：router → ElementPlus → mount（顺序影响插件初始化）
 */
function bootstrapApp() {
  const app = createApp(App);   // 创建 Vue 应用实例（根组件为 App.vue）
  app.use(router);              // 注册路由插件（提供 <router-view> 和 <router-link>）
  app.use(ElementPlus);         // 注册 Element Plus（提供全局 UI 组件和 ElMessage 等）
  app.mount("#app");            // 挂载到 index.html 中的 #app 元素
}

bootstrapApp();
