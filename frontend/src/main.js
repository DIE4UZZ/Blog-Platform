import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router/index.js";
import "./index.css";

/**
 * Bootstrap the Vue application with router and UI library.
 * @returns {void} No return value.
 */
function bootstrapApp() {
  const app = createApp(App);
  app.use(router);
  app.use(ElementPlus);
  app.mount("#app");
}

bootstrapApp();
