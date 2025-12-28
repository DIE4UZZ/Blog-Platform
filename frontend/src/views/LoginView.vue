<template>
  <AuthLayout>
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.35em] text-slate">Sign In</p>
        <h2 class="mt-3 text-[clamp(2rem,4vw,3rem)] font-semibold text-ink">
          欢迎回来
        </h2>
      </div>
      <router-link
        class="text-sm font-semibold text-ink/80 transition hover:text-ink"
        to="/register"
      >
        创建账号
      </router-link>
    </div>

    <p class="mt-4 text-base leading-relaxed text-slate">
      使用你的邮箱继续，开始浏览个性化内容推荐。
    </p>

    <el-form
      ref="formRef"
      class="auth-form mt-8 space-y-6"
      :model="form"
      :rules="rules"
      label-position="top"
    >
      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="form.email"
          class="auth-input w-full"
          placeholder="you@example.com"
          size="large"
        />
      </el-form-item>
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
      <el-button
        class="auth-button w-full"
        type="primary"
        :loading="isSubmitting"
        @click="handleSubmit"
      >
        登录
      </el-button>
    </el-form>

    <p class="mt-6 text-sm text-slate">
      登录即表示你已阅读并同意我们的服务协议与隐私政策。
    </p>
  </AuthLayout>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import AuthLayout from "../components/AuthLayout.vue";
import { loginUser } from "../services/user.js";
import { setAuthToken } from "../services/http.js";

const formRef = ref();
const form = reactive({
  email: "",
  password: "",
});
const isSubmitting = ref(false);

/**
 * Validate email format for Element Plus form.
 * @param {object} _rule Validation rule.
 * @param {string} value Field value.
 * @param {(error?: Error) => void} callback Validation callback.
 * @returns {void} No return value.
 */
function validateEmail(_rule, value, callback) {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const normalizedValue = String(value || "").trim();
  if (!normalizedValue) {
    callback(new Error("请输入邮箱"));
    return;
  }
  if (!emailPattern.test(normalizedValue)) {
    callback(new Error("邮箱格式不正确"));
    return;
  }
  callback();
}

const rules = {
  email: [{ validator: validateEmail, trigger: "blur" }],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 位", trigger: "blur" },
  ],
};

/**
 * Submit login form data and persist token on success.
 * @returns {Promise<void>} No return value.
 */
async function handleSubmit() {
  if (!formRef.value) return;
  try {
    isSubmitting.value = true;
    await formRef.value.validate();
    const data = await loginUser({
      email: form.email,
      password: form.password,
    });
    if (data?.token) {
      setAuthToken(data.token);
    }
    ElMessage.success("登录成功，欢迎回来。");
  } finally {
    isSubmitting.value = false;
  }
}
</script>
