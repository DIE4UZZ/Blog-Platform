<template>
  <AuthLayout>
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.35em] text-slate">Create</p>
        <h2 class="mt-3 text-[clamp(2rem,4vw,3rem)] font-semibold text-ink">创建账号</h2>
      </div>
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

    <el-form
      ref="formRef"
      class="auth-form mt-8 space-y-6"
      :model="form"
      :rules="rules"
      label-position="top"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          class="auth-input w-full"
          placeholder="2-32 位用户名"
          size="large"
        />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="form.email"
          class="auth-input w-full"
          placeholder="you@example.com"
          size="large"
        />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input
          v-model="form.phone"
          class="auth-input w-full"
          placeholder="可选手机号"
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
        注册账号
      </el-button>
    </el-form>

    <p class="mt-6 text-sm text-slate">
      注册即表示你已阅读并同意服务协议与隐私政策。
    </p>
  </AuthLayout>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AuthLayout from "../components/AuthLayout.vue";
import { registerUser } from "../services/user.js";

const router = useRouter();
const formRef = ref();
const form = reactive({
  username: "",
  email: "",
  phone: "",
  password: "",
});
const isSubmitting = ref(false);

function validateEmail(_rule, value, callback) {
  const normalizedValue = String(value || "").trim();
  if (!normalizedValue) {
    callback();
    return;
  }
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(normalizedValue)) {
    callback(new Error("邮箱格式不正确"));
    return;
  }
  callback();
}

function validatePhone(_rule, value, callback) {
  const normalizedValue = String(value || "").trim();
  if (!normalizedValue) {
    callback();
    return;
  }
  const phonePattern = /^[0-9+\-\s]{6,32}$/;
  if (!phonePattern.test(normalizedValue)) {
    callback(new Error("手机号格式不正确"));
    return;
  }
  callback();
}

function validateContact(_rule, _value, callback) {
  if (!String(form.email || "").trim() && !String(form.phone || "").trim()) {
    callback(new Error("邮箱和手机号至少填写一项"));
    return;
  }
  callback();
}

const rules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 2, max: 32, message: "用户名长度需为 2-32 位", trigger: "blur" },
  ],
  email: [
    { validator: validateEmail, trigger: "blur" },
    { validator: validateContact, trigger: "blur" },
  ],
  phone: [
    { validator: validatePhone, trigger: "blur" },
    { validator: validateContact, trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 位", trigger: "blur" },
  ],
};

/**
 * 提交注册表单并在成功后跳转到登录页。
 * @returns {Promise<void>} 无返回值。
 */
async function handleSubmit() {
  if (!formRef.value) return;
  try {
    isSubmitting.value = true;
    await formRef.value.validate();
    await registerUser({
      username: form.username.trim(),
      email: form.email.trim() || undefined,
      phone: form.phone.trim() || undefined,
      password: form.password,
    });
    ElMessage.success("注册成功，请登录。");
    await router.push("/login");
  } finally {
    isSubmitting.value = false;
  }
}
</script>
