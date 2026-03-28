<template>
  <AppLayout>
    <SectionCard title="用户管理">
      <el-table :data="userList" v-loading="isUserLoading">
        <el-table-column prop="user_id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="role" label="角色" width="120" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="changeRole(row, 'user')">设为用户</el-button>
            <el-button size="small" type="primary" @click="changeRole(row, 'admin')">设为管理员</el-button>
          </template>
        </el-table-column>
      </el-table>
    </SectionCard>

    <SectionCard title="文章审核">
      <el-table :data="articleList" v-loading="isArticleLoading">
        <el-table-column prop="article_id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column prop="author" label="作者" width="160" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="reviewArticle(row, 'published')">通过</el-button>
            <el-button size="small" @click="reviewArticle(row, 'draft')">转草稿</el-button>
            <el-button size="small" type="danger" @click="reviewArticle(row, 'rejected')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </SectionCard>

    <SectionCard title="异常内容巡检">
      <el-table :data="abnormalList" v-loading="isAbnormalLoading">
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="target_id" label="目标ID" width="100" />
        <el-table-column prop="snippet" label="内容片段" min-width="220" />
        <el-table-column label="命中词" min-width="180">
          <template #default="{ row }">{{ (row.hit_keywords || []).join(", ") }}</template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="180" />
      </el-table>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import {
  fetchAbnormalContent,
  fetchAdminArticles,
  fetchAdminUsers,
  reviewAdminArticle,
  updateAdminUserRole,
} from "../services/admin.js";

const userList = ref([]);
const articleList = ref([]);
const abnormalList = ref([]);
const isUserLoading = ref(false);
const isArticleLoading = ref(false);
const isAbnormalLoading = ref(false);

async function loadUsers() {
  try {
    isUserLoading.value = true;
    const data = await fetchAdminUsers({ page: 1, page_size: 20 });
    userList.value = data?.list || [];
  } finally {
    isUserLoading.value = false;
  }
}

async function loadArticles() {
  try {
    isArticleLoading.value = true;
    const data = await fetchAdminArticles({ page: 1, page_size: 20 });
    articleList.value = data?.list || [];
  } finally {
    isArticleLoading.value = false;
  }
}

async function loadAbnormal() {
  try {
    isAbnormalLoading.value = true;
    const data = await fetchAbnormalContent({ page: 1, page_size: 20 });
    abnormalList.value = data?.list || [];
  } finally {
    isAbnormalLoading.value = false;
  }
}

async function changeRole(row, role) {
  await updateAdminUserRole({ user_id: row.user_id, role });
  ElMessage.success("角色更新成功");
  await loadUsers();
}

async function reviewArticle(row, status) {
  await reviewAdminArticle({ article_id: row.article_id, status });
  ElMessage.success("文章状态更新成功");
  await loadArticles();
}

onMounted(() => {
  loadUsers();
  loadArticles();
  loadAbnormal();
});
</script>
