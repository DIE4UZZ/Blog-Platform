<template>
  <AppLayout>
    <div class="profile-grid">
      <SectionCard title="个人信息">
        <div v-if="isUserLoading" class="skeleton-list">
          <div v-for="item in 3" :key="item" class="skeleton-line"></div>
        </div>
        <div v-else-if="!userInfo">
          <EmptyState title="暂无用户信息" message="请先登录" />
        </div>
        <div v-else class="profile-info">
          <div>
            <p class="meta-text">用户名</p>
            <p class="profile-value">{{ userInfo.username || "用户" }}</p>
          </div>
          <div>
            <p class="meta-text">邮箱</p>
            <p class="profile-value">{{ userInfo.email || "--" }}</p>
          </div>
          <div>
            <p class="meta-text">手机号</p>
            <p class="profile-value">{{ userInfo.phone || "--" }}</p>
          </div>
          <div>
            <p class="meta-text">创建时间</p>
            <p class="profile-value">{{ formatDate(userInfo.create_time) }}</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="兴趣标签">
        <el-form label-position="top">
          <el-form-item label="标签（逗号分隔）">
            <el-input v-model="preferenceTags" placeholder="AI,Python,推荐系统" />
          </el-form-item>
          <el-button class="solid-button" :loading="isSaving" @click="savePreference">保存偏好</el-button>
        </el-form>
      </SectionCard>
    </div>

    <SectionCard title="我的文章">
      <div v-if="isArticlesLoading" class="skeleton-list">
        <div v-for="item in 4" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="myArticles.length === 0">
        <EmptyState title="暂无文章" message="去发布你的第一篇文章" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in myArticles" :key="item.article_id" class="list-card">
          <div class="list-card__meta">
            <span class="tag-chip">{{ item.category || "未分类" }}</span>
            <span class="meta-text">{{ formatDate(item.create_time) }}</span>
          </div>
          <h3 class="list-card__title">{{ item.title }}</h3>
          <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
          <div class="list-card__footer">
            <span class="meta-text">状态：{{ item.status || "published" }}</span>
            <div class="list-actions">
              <router-link class="text-link" :to="`/editor/${item.article_id}`">编辑</router-link>
              <button type="button" class="text-link text-red-500" @click="removeArticle(item)">删除</button>
            </div>
          </div>
        </article>
      </div>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { deleteArticle, fetchMyArticles } from "../services/article.js";
import { fetchUserInfo, setCachedUserInfo, updatePreferenceTags } from "../services/user.js";

const userInfo = ref(null);
const preferenceTags = ref("");
const myArticles = ref([]);
const isUserLoading = ref(false);
const isArticlesLoading = ref(false);
const isSaving = ref(false);

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).split(" ")[0];
}

async function loadUserInfo() {
  try {
    isUserLoading.value = true;
    const data = await fetchUserInfo();
    userInfo.value = data || null;
    preferenceTags.value = data?.preference_tags || "";
    setCachedUserInfo(data || {});
  } finally {
    isUserLoading.value = false;
  }
}

async function loadMyArticles() {
  try {
    isArticlesLoading.value = true;
    const data = await fetchMyArticles({ page: 1, page_size: 20 });
    myArticles.value = data?.list || [];
  } finally {
    isArticlesLoading.value = false;
  }
}

async function savePreference() {
  try {
    isSaving.value = true;
    await updatePreferenceTags({
      preference_tags: preferenceTags.value.trim(),
    });
    ElMessage.success("偏好标签已更新");
    await loadUserInfo();
  } finally {
    isSaving.value = false;
  }
}

async function removeArticle(item) {
  await deleteArticle(item.article_id);
  ElMessage.success("文章已删除");
  await loadMyArticles();
}

onMounted(() => {
  loadUserInfo();
  loadMyArticles();
});
</script>
