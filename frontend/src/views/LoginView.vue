<template>
  <AuthLayout>
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.35em] text-slate">Sign In</p>
        <h2 class="mt-3 text-[clamp(2rem,4vw,3rem)] font-semibold text-ink">欢迎回来</h2>
      </div>
      <router-link class="text-sm font-semibold text-ink/80 transition hover:text-ink" to="/register">
        创建账号
      </router-link>
    </div>

    <p class="mt-4 text-base leading-relaxed text-slate">支持用户名、邮箱或手机号登录。</p>

    <el-form ref="formRef" class="auth-form mt-8 space-y-6" :model="form" :rules="rules" label-position="top">
      <el-form-item label="账号" prop="account">
        <el-input v-model="form.account" class="auth-input w-full" placeholder="用户名 / 邮箱 / 手机号" size="large" />
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
      <el-button class="auth-button w-full" type="primary" :loading="isSubmitting" @click="handleSubmit">
        登录
      </el-button>
    </el-form>
  </AuthLayout>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AuthLayout from "../components/AuthLayout.vue";
import { loginUser, refreshCurrentUserInfo } from "../services/user.js";
import { setAuthToken } from "../services/http.js";

const router = useRouter();
const formRef = ref();
const isSubmitting = ref(false);
const form = reactive({
  account: "",
  password: "",
});

const rules = {
  account: [
    {
      validator(_rule, value, callback) {
        if (!String(value || "").trim()) {
          callback(new Error("请输入账号"));
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 位", trigger: "blur" },
  ],
};

async function handleSubmit() {
  if (!formRef.value) return;
  try {
    isSubmitting.value = true;
    await formRef.value.validate();
    const data = await loginUser({
      account: form.account.trim(),
      password: form.password,
    });
    if (data?.token) {
      setAuthToken(data.token);
    }
    await refreshCurrentUserInfo();
    ElMessage.success("登录成功");
    const redirect = String(router.currentRoute.value.query.redirect || "/");
    await router.push(redirect);
  } finally {
    isSubmitting.value = false;
  }
}
</script>
