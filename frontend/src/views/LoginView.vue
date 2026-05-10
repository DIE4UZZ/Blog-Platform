<!--
  LoginView.vue —— 用户登录页面

  功能说明：
    - 提供用户名/邮箱/手机号 + 密码的登录表单
    - 表单校验：账号非空、密码至少 6 位
    - 登录成功后：保存 JWT Token → 刷新用户信息缓存 → 跳转目标页
    - 支持 redirect 参数：从受保护页面跳转过来时，登录后自动回跳

  组件依赖：
    - AuthLayout：认证页面布局（左侧品牌区 + 右侧表单区）
    - loginUser：调用 POST /user/login 接口
    - setAuthToken：将 Token 写入 localStorage
    - refreshCurrentUserInfo：从服务端拉取用户信息并缓存

  路由：/login（无需登录，已登录时路由守卫会重定向到首页）
-->
<template>
  <!-- 使用认证专用布局（AuthLayout 提供左侧品牌区 + 右侧表单区的双栏布局） -->
  <AuthLayout>
    <!-- 页面标题区：左侧标题 + 右侧"创建账号"跳转链接 -->
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.35em] text-slate">Sign In</p>
        <h2 class="mt-3 text-[clamp(2rem,4vw,3rem)] font-semibold text-ink">欢迎回来</h2>
      </div>
      <!-- 跳转到注册页 -->
      <router-link class="text-sm font-semibold text-ink/80 transition hover:text-ink" to="/register">
        创建账号
      </router-link>
    </div>

    <p class="mt-4 text-base leading-relaxed text-slate">支持用户名、邮箱或手机号登录。</p>

    <!-- 登录表单：使用 Element Plus el-form 组件，绑定 rules 进行前端校验 -->
    <el-form ref="formRef" class="auth-form mt-8 space-y-6" :model="form" :rules="rules" label-position="top">
      <!-- 账号输入框：支持用户名/邮箱/手机号 -->
      <el-form-item label="账号" prop="account">
        <el-input v-model="form.account" class="auth-input w-full" placeholder="用户名 / 邮箱 / 手机号" size="large" />
      </el-form-item>
      <!-- 密码输入框：type="password" + show-password 切换可见性 -->
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          class="auth-input w-full"
          placeholder="至少 6 位"
          size="large"
          type="password"
          show-password
        />
      </el-form-item>
      <!-- 提交按钮：loading 状态防止重复提交 -->
      <el-button class="auth-button w-full" type="primary" :loading="isSubmitting" @click="handleSubmit">
        登录
      </el-button>
    </el-form>
  </AuthLayout>
</template>

<script setup>
/**
 * LoginView 脚本逻辑
 *
 * 状态：
 *   - formRef     : el-form 实例引用（用于调用 validate 方法）
 *   - isSubmitting: 提交中标志（防止重复点击）
 *   - form        : 表单数据（account + password）
 *   - rules       : 表单校验规则
 *
 * 核心流程（handleSubmit）：
 *   1. 调用 formRef.validate() 触发前端校验
 *   2. 调用 loginUser() 发起登录请求
 *   3. 将返回的 token 写入 localStorage（setAuthToken）
 *   4. 调用 refreshCurrentUserInfo() 拉取并缓存用户信息
 *   5. 跳转到 redirect 参数指定的页面（默认首页）
 */
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AuthLayout from "../components/AuthLayout.vue";
import { loginUser, refreshCurrentUserInfo } from "../services/user.js";
import { setAuthToken } from "../services/http.js";

const router = useRouter();
const formRef = ref();           // el-form 实例引用
const isSubmitting = ref(false); // 提交中标志（控制按钮 loading 状态）

// 表单数据
const form = reactive({
  account: "",   // 账号（用户名/邮箱/手机号）
  password: "",  // 密码
});

// 表单校验规则
const rules = {
  account: [
    {
      // 自定义校验：账号不能为空（trim 后判断）
      validator(_rule, value, callback) {
        if (!String(value || "").trim()) {
          callback(new Error("请输入账号"));
          return;
        }
        callback();
      },
      trigger: "blur",  // 失焦时触发校验
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 位", trigger: "blur" },
  ],
};

/**
 * 处理登录表单提交。
 *
 * 流程：
 *   1. 触发 el-form 前端校验（validate）
 *   2. 调用 loginUser API 发起登录请求
 *   3. 保存 JWT Token 到 localStorage
 *   4. 刷新用户信息缓存（触发导航栏更新）
 *   5. 跳转到目标页面（支持 redirect 参数回跳）
 */
async function handleSubmit() {
  if (!formRef.value) return;
  try {
    isSubmitting.value = true;
    await formRef.value.validate();  // 触发前端表单校验，不通过则抛出异常
    const data = await loginUser({
      account: form.account.trim(),  // 去除首尾空格
      password: form.password,
    });
    if (data?.token) {
      setAuthToken(data.token);  // 将 JWT Token 写入 localStorage
    }
    await refreshCurrentUserInfo();  // 从服务端拉取用户信息并缓存到 localStorage
    ElMessage.success("登录成功");
    // 跳转到 redirect 参数指定的页面，默认跳转首页
    const redirect = String(router.currentRoute.value.query.redirect || "/");
    await router.push(redirect);
  } finally {
    isSubmitting.value = false;  // 无论成功失败，都恢复按钮状态
  }
}
</script>
