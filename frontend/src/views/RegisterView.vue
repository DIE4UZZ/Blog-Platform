<!--
  RegisterView.vue —— 用户注册页面

  功能说明：
    - 提供用户名 + 邮箱/手机号 + 密码的注册表单
    - 表单校验：
        * 用户名：必填，2-32 位
        * 邮箱：可选，但需符合邮箱格式
        * 手机号：可选，但需符合手机号格式
        * 邮箱和手机号至少填写一项（validateContact 联合校验）
        * 密码：必填，至少 6 位
    - 注册成功后跳转到登录页

  组件依赖：
    - AuthLayout：认证页面布局（左侧品牌区 + 右侧表单区）
    - registerUser：调用 POST /user/register 接口

  路由：/register（无需登录，已登录时路由守卫会重定向到首页）
-->
<template>
  <!-- 使用认证专用布局 -->
  <AuthLayout>
    <!-- 页面标题区：左侧标题 + 右侧"返回登录"跳转链接 -->
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.35em] text-slate">Create</p>
        <h2 class="mt-3 text-[clamp(2rem,4vw,3rem)] font-semibold text-ink">创建账号</h2>
      </div>
      <!-- 跳转到登录页 -->
      <router-link
        class="text-sm font-semibold text-ink/80 transition hover:text-ink"
        to="/login"
      >
        返回登录
      </router-link>
    </div>

    <p class="mt-4 text-base leading-relaxed text-slate">
      设置用户名，并填写邮箱或手机号中的至少一项即可完成注册。
    </p>

    <!-- 注册表单：使用 Element Plus el-form，绑定 rules 进行前端校验 -->
    <el-form
      ref="formRef"
      class="auth-form mt-8 space-y-6"
      :model="form"
      :rules="rules"
      label-position="top"
    >
      <!-- 用户名：必填，2-32 位 -->
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          class="auth-input w-full"
          placeholder="2-32 位用户名"
          size="large"
        />
      </el-form-item>
      <!-- 邮箱：可选，但与手机号至少填一项 -->
      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="form.email"
          class="auth-input w-full"
          placeholder="you@example.com"
          size="large"
        />
      </el-form-item>
      <!-- 手机号：可选，但与邮箱至少填一项 -->
      <el-form-item label="手机号" prop="phone">
        <el-input
          v-model="form.phone"
          class="auth-input w-full"
          placeholder="可选手机号"
          size="large"
        />
      </el-form-item>
      <!-- 密码：必填，至少 6 位，支持显示/隐藏切换 -->
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
      <el-button
        class="auth-button w-full"
        type="primary"
        :loading="isSubmitting"
        @click="handleSubmit"
      >
        注册账号
      </el-button>
    </el-form>

    <p class="mt-6 text-sm text-slate">
      注册即表示你已阅读并同意服务协议与隐私政策。
    </p>
  </AuthLayout>
</template>

<script setup>
/**
 * RegisterView 脚本逻辑
 *
 * 状态：
 *   - formRef     : el-form 实例引用（用于调用 validate 方法）
 *   - form        : 表单数据（username/email/phone/password）
 *   - isSubmitting: 提交中标志（防止重复点击）
 *   - rules       : 表单校验规则（含自定义校验函数）
 *
 * 自定义校验函数：
 *   - validateEmail   : 邮箱格式校验（可为空，非空时校验格式）
 *   - validatePhone   : 手机号格式校验（可为空，非空时校验格式）
 *   - validateContact : 联合校验（邮箱和手机号至少填一项）
 *
 * 核心流程（handleSubmit）：
 *   1. 调用 formRef.validate() 触发前端校验
 *   2. 调用 registerUser() 发起注册请求
 *   3. 注册成功后跳转到登录页
 */
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AuthLayout from "../components/AuthLayout.vue";
import { registerUser } from "../services/user.js";

const router = useRouter();
const formRef = ref();           // el-form 实例引用
const isSubmitting = ref(false); // 提交中标志

// 表单数据
const form = reactive({
  username: "",  // 用户名（必填）
  email: "",     // 邮箱（与 phone 至少填一项）
  phone: "",     // 手机号（与 email 至少填一项）
  password: "",  // 密码（必填，至少 6 位）
});

/**
 * 邮箱格式校验（自定义校验函数）。
 * 邮箱可为空（空时跳过格式校验），非空时必须符合邮箱格式。
 */
function validateEmail(_rule, value, callback) {
  const normalizedValue = String(value || "").trim();
  if (!normalizedValue) {
    callback();  // 邮箱为空时不报错（由 validateContact 负责联合校验）
    return;
  }
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(normalizedValue)) {
    callback(new Error("邮箱格式不正确"));
    return;
  }
  callback();
}

/**
 * 手机号格式校验（自定义校验函数）。
 * 手机号可为空（空时跳过格式校验），非空时必须符合手机号格式。
 * 支持国际格式（含 +、-、空格），长度 6-32 位。
 */
function validatePhone(_rule, value, callback) {
  const normalizedValue = String(value || "").trim();
  if (!normalizedValue) {
    callback();  // 手机号为空时不报错（由 validateContact 负责联合校验）
    return;
  }
  const phonePattern = /^[0-9+\-\s]{6,32}$/;
  if (!phonePattern.test(normalizedValue)) {
    callback(new Error("手机号格式不正确"));
    return;
  }
  callback();
}

/**
 * 联合校验：邮箱和手机号至少填写一项。
 * 同时绑定到 email 和 phone 字段，任一字段失焦时触发。
 */
function validateContact(_rule, _value, callback) {
  if (!String(form.email || "").trim() && !String(form.phone || "").trim()) {
    callback(new Error("邮箱和手机号至少填写一项"));
    return;
  }
  callback();
}

// 表单校验规则
const rules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 2, max: 32, message: "用户名长度需为 2-32 位", trigger: "blur" },
  ],
  email: [
    { validator: validateEmail, trigger: "blur" },      // 邮箱格式校验
    { validator: validateContact, trigger: "blur" },    // 联合校验（至少填一项）
  ],
  phone: [
    { validator: validatePhone, trigger: "blur" },      // 手机号格式校验
    { validator: validateContact, trigger: "blur" },    // 联合校验（至少填一项）
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 位", trigger: "blur" },
  ],
};

/**
 * 处理注册表单提交。
 *
 * 流程：
 *   1. 触发 el-form 前端校验（validate）
 *   2. 调用 registerUser API 发起注册请求
 *   3. 注册成功后弹出提示并跳转到登录页
 *
 * 注意：空字符串的 email/phone 传 undefined（后端不接受空字符串）
 *
 * @returns {Promise<void>}
 */
async function handleSubmit() {
  if (!formRef.value) return;
  try {
    isSubmitting.value = true;
    await formRef.value.validate();  // 触发前端表单校验
    await registerUser({
      username: form.username.trim(),
      email: form.email.trim() || undefined,    // 空字符串转为 undefined
      phone: form.phone.trim() || undefined,    // 空字符串转为 undefined
      password: form.password,
    });
    ElMessage.success("注册成功，请登录。");
    await router.push("/login");  // 注册成功后跳转到登录页
  } finally {
    isSubmitting.value = false;  // 无论成功失败，都恢复按钮状态
  }
}
</script>
