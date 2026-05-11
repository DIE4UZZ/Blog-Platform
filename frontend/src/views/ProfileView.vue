<template>
  <AppLayout>
    <!-- ===== 方案2: Bento Grid 个人概览 ===== -->
    <div class="profile-overview">
      <!-- 主卡：头像 + 基本信息 -->
      <SectionCard>
        <div v-if="isUserLoading" class="skeleton-list">
          <div v-for="item in 3" :key="item" class="skeleton-line"></div>
        </div>
        <div v-else-if="!userInfo">
          <EmptyState title="暂无用户信息" message="请先登录" />
        </div>
        <div v-else class="profile-hero">
          <div class="profile-hero__main">
            <!-- 方案3: 可点击头像 -->
            <div class="profile-avatar profile-avatar--interactive" @click="showEditDialog = true">
              <span>{{ profileInitial }}</span>
              <div class="profile-avatar__overlay">
                <el-icon :size="20"><Edit /></el-icon>
              </div>
            </div>
            <div class="profile-hero__copy">
              <p class="profile-hero__eyebrow">Profile</p>
              <h2 class="profile-hero__name">{{ userInfo.username || "用户" }}</h2>
              <p class="profile-hero__meta">
                {{ userInfo.email || "未填写邮箱" }}
                <span class="meta-divider"></span>
                {{ userInfo.phone || "未填写手机号" }}
              </p>
            </div>
          </div>
          <div class="profile-hero__actions">
            <el-button class="ghost-button ghost-button--compact" @click="showEditDialog = true">
              <el-icon style="margin-right: 6px"><Edit /></el-icon>编辑资料
            </el-button>
          </div>
        </div>
      </SectionCard>

      <!-- Bento 统计卡片 - 均匀 6 列 -->
      <div class="profile-stats-grid">
        <div class="profile-bento__stat profile-bento__stat--accent">
          <div class="bento-stat__icon">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <el-statistic :value="myArticles.length" title="文章数量" />
        </div>

        <div class="profile-bento__stat profile-bento__stat--warm">
          <div class="bento-stat__icon bento-stat__icon--warm">
            <el-icon :size="24"><UserFilled /></el-icon>
          </div>
          <el-statistic :value="userInfo?.follower_count || 0" title="关注者" />
        </div>

        <div class="profile-bento__stat profile-bento__stat--cool">
          <div class="bento-stat__icon bento-stat__icon--cool">
            <el-icon :size="24"><Star /></el-icon>
          </div>
          <el-statistic :value="userInfo?.following_count || 0" title="关注中" />
        </div>

        <div class="profile-bento__stat">
          <div class="bento-stat__icon bento-stat__icon--muted">
            <el-icon :size="24"><Bell /></el-icon>
          </div>
          <el-statistic :value="userInfo?.unread_notification_count || 0" title="未读通知" />
        </div>

        <div class="profile-bento__stat">
          <div class="bento-stat__icon bento-stat__icon--muted">
            <el-icon :size="24"><Clock /></el-icon>
          </div>
          <div class="bento-stat__text">
            <span class="bento-stat__label">加入时间</span>
            <strong class="bento-stat__value">{{ formatDate(userInfo?.create_time) }}</strong>
          </div>
        </div>

        <div class="profile-bento__stat">
          <div class="bento-stat__icon bento-stat__icon--muted">
            <el-icon :size="24"><PriceTag /></el-icon>
          </div>
          <el-statistic :value="preferenceTagList.length" title="兴趣标签" />
        </div>
      </div>

      <!-- 方案4: 迷你阅读活跃度 -->
      <SectionCard title="阅读活跃度">
        <div class="activity-heatmap">
          <div
            v-for="(level, idx) in activityData"
            :key="idx"
            class="activity-cell"
            :class="`activity-cell--level-${level}`"
            :title="`${activityLabels[idx]}: ${level > 0 ? level + ' 次阅读' : '无记录'}`"
          ></div>
        </div>
        <div class="activity-legend">
          <span class="meta-text">近30天</span>
          <div class="activity-legend__scale">
            <span class="meta-text">少</span>
            <div class="activity-cell activity-cell--level-0"></div>
            <div class="activity-cell activity-cell--level-1"></div>
            <div class="activity-cell activity-cell--level-2"></div>
            <div class="activity-cell activity-cell--level-3"></div>
            <div class="activity-cell activity-cell--level-4"></div>
            <span class="meta-text">多</span>
          </div>
        </div>
      </SectionCard>
    </div>

    <!-- 兴趣标签 -->
    <SectionCard title="兴趣标签">
      <p class="section-intro">
        用更直观的方式维护兴趣偏好。新标签会生成气泡，点击气泡右上角即可删除。
      </p>
      <div class="tag-bubble-editor">
        <div class="tag-bubble-input">
          <el-input
            v-model="newTag"
            placeholder="输入标签后回车或点击添加"
            @keyup.enter="addTag"
          />
          <el-button class="solid-button" :disabled="!newTag.trim()" @click="addTag">
            添加标签
          </el-button>
        </div>

        <div v-if="preferenceTagList.length" class="tag-bubble-cloud" :style="bubbleCloudStyle">
          <button
            v-for="tag in preferenceTagList"
            :key="tag"
            type="button"
            class="tag-bubble"
            @click="removeTag(tag)"
          >
            <span class="tag-bubble__text">{{ tag }}</span>
            <span class="tag-bubble__close">×</span>
          </button>
        </div>
        <div v-else class="tag-bubble-empty">
          <EmptyState
            title="还没有兴趣标签"
            message="添加几个你感兴趣的主题，后续推荐会更贴近你的阅读偏好。"
          />
        </div>

        <div class="tag-bubble-toolbar">
          <span class="meta-text">当前标签会以逗号分隔的形式保存。</span>
          <el-button class="solid-button" :loading="isSaving" @click="savePreference">
            保存偏好
          </el-button>
        </div>
      </div>
    </SectionCard>

    <!-- ===== 方案1: Tab 化内容区 + 懒加载 ===== -->
    <SectionCard>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的文章" name="articles">
          <template #label>
            <span class="tab-label">
              <el-icon><Document /></el-icon> 我的文章
              <el-badge v-if="myArticles.length" :value="myArticles.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <div class="tab-header">
            <router-link class="ghost-button ghost-button--compact" to="/editor">
              <el-icon style="margin-right: 4px"><Plus /></el-icon>写新文章
            </router-link>
          </div>
          <div v-if="isArticlesLoading" class="skeleton-list">
            <div v-for="item in 4" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="myArticles.length === 0">
            <EmptyState title="暂无文章" message="去发布你的第一篇文章" />
          </div>
          <div v-else class="card-list">
            <article v-for="item in myArticles" :key="item.article_id" class="list-card list-card--horizontal">
              <!-- 方案5: 封面缩略图 -->
              <div v-if="extractCover(item)" class="list-card__cover">
                <img :src="extractCover(item)" :alt="item.title" loading="lazy" />
              </div>
              <div class="list-card__body">
                <div class="list-card__meta">
                  <span class="tag-chip">{{ item.category || "未分类" }}</span>
                  <span class="meta-text">{{ formatDate(item.create_time) }}</span>
                </div>
                <h3 class="list-card__title">{{ item.title }}</h3>
                <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
                <div class="list-card__footer">
                  <span class="meta-text">状态：{{ item.status || "published" }}</span>
                  <div class="list-actions">
                    <router-link class="ghost-button ghost-button--compact" :to="`/editor/${item.article_id}`">
                      编辑
                    </router-link>
                    <el-popconfirm title="确定删除这篇文章吗？" confirm-button-text="删除" cancel-button-text="取消" @confirm="removeArticle(item)">
                      <template #reference>
                        <el-button class="ghost-button ghost-button--danger ghost-button--compact">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的收藏" name="collections" :lazy="true">
          <template #label>
            <span class="tab-label">
              <el-icon><Star /></el-icon> 我的收藏
              <el-badge v-if="collections.length" :value="collections.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <div v-if="isCollectionsLoading" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="collections.length === 0">
            <EmptyState title="还没有收藏文章" message="看到喜欢的文章后，可以在详情页加入收藏。" />
          </div>
          <div v-else class="card-list">
            <article v-for="item in collections" :key="item.article_id" class="list-card list-card--horizontal">
              <div v-if="extractCover(item)" class="list-card__cover">
                <img :src="extractCover(item)" :alt="item.title" loading="lazy" />
              </div>
              <div class="list-card__body">
                <div class="list-card__meta">
                  <span class="tag-chip">{{ item.category || "未分类" }}</span>
                  <span class="meta-text">收藏于 {{ formatDate(item.collected_at) }}</span>
                </div>
                <h3 class="list-card__title">{{ item.title }}</h3>
                <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
                <div class="list-card__footer">
                  <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
                  <div class="list-actions">
                    <router-link class="ghost-button ghost-button--compact" :to="`/articles/${item.article_id}`">
                      阅读
                    </router-link>
                    <el-popconfirm title="确定取消收藏吗？" confirm-button-text="取消收藏" cancel-button-text="保留" @confirm="removeCollection(item)">
                      <template #reference>
                        <el-button class="ghost-button ghost-button--danger ghost-button--compact">取消收藏</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="阅读历史" name="history" :lazy="true">
          <template #label>
            <span class="tab-label">
              <el-icon><Clock /></el-icon> 阅读历史
            </span>
          </template>
          <div v-if="isHistoryLoading" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="historyList.length === 0">
            <EmptyState title="暂无阅读历史" message="开始阅读文章后，这里会自动沉淀你的访问记录。" />
          </div>
          <div v-else class="card-list">
            <article v-for="item in historyList" :key="item.article_id" class="list-card list-card--horizontal">
              <div v-if="extractCover(item)" class="list-card__cover">
                <img :src="extractCover(item)" :alt="item.title" loading="lazy" />
              </div>
              <div class="list-card__body">
                <div class="list-card__meta">
                  <span class="tag-chip">{{ item.category || "未分类" }}</span>
                  <span class="meta-text">最近阅读 {{ formatDate(item.last_read_time) }}</span>
                </div>
                <h3 class="list-card__title">{{ item.title }}</h3>
                <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
                <!-- 方案5: 阅读进度条 -->
                <div class="list-card__progress">
                  <div class="list-card__progress-bar">
                    <div class="list-card__progress-fill" :style="{ width: formatDepth(item.max_scroll_depth) }"></div>
                  </div>
                  <span class="meta-text">阅读进度 {{ formatDepth(item.max_scroll_depth) }}</span>
                </div>
                <div class="list-card__stats">
                  <span class="list-stat">阅读 {{ item.read_count || 0 }} 次</span>
                  <span class="list-stat">时长 {{ item.last_read_duration || 0 }}s</span>
                </div>
                <div class="list-card__footer">
                  <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
                  <router-link class="ghost-button ghost-button--compact" :to="`/articles/${item.article_id}`">继续阅读</router-link>
                </div>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="稍后读" name="readlater" :lazy="true">
          <template #label>
            <span class="tab-label">
              <el-icon><Reading /></el-icon> 稍后读
              <el-badge v-if="readLaterList.length" :value="readLaterList.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <div v-if="isReadLaterLoading" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="readLaterList.length === 0">
            <EmptyState title="稍后读列表为空" message="可以把还没来得及细读的文章先存起来。" />
          </div>
          <div v-else class="card-list">
            <article v-for="item in readLaterList" :key="item.article_id" class="list-card list-card--horizontal">
              <div v-if="extractCover(item)" class="list-card__cover">
                <img :src="extractCover(item)" :alt="item.title" loading="lazy" />
              </div>
              <div class="list-card__body">
                <div class="list-card__meta">
                  <span class="tag-chip">{{ item.category || "未分类" }}</span>
                  <span class="meta-text">加入于 {{ formatDate(item.saved_at) }}</span>
                </div>
                <h3 class="list-card__title">{{ item.title }}</h3>
                <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
                <div class="list-card__footer">
                  <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
                  <div class="list-actions">
                    <router-link class="ghost-button ghost-button--compact" :to="`/articles/${item.article_id}`">
                      去阅读
                    </router-link>
                    <el-popconfirm title="确定移出稍后读吗？" confirm-button-text="移出" cancel-button-text="保留" @confirm="removeReadLater(item)">
                      <template #reference>
                        <el-button class="ghost-button ghost-button--danger ghost-button--compact">移出列表</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </SectionCard>

    <!-- ===== 方案3: 编辑资料弹窗 ===== -->
    <el-dialog v-model="showEditDialog" title="编辑个人资料" width="480px" :close-on-click-modal="false">
      <el-form label-position="top" class="profile-edit-form">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="个人简介">
          <el-input v-model="editForm.bio" type="textarea" :rows="3" placeholder="介绍一下自己" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button class="solid-button" @click="handleSaveProfile">保存修改</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Document, Star, UserFilled, Bell, Clock, PriceTag, Edit, Plus, Reading } from "@element-plus/icons-vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { deleteArticle, fetchMyArticles, toggleCollect } from "../services/article.js";
import { fetchCollections, fetchReadHistory, fetchReadLater, toggleReadLater } from "../services/library.js";
import { fetchUserInfo, setCachedUserInfo, updatePreferenceTags, updateUserProfile } from "../services/user.js";

const userInfo = ref(null);
const preferenceTags = ref("");
const newTag = ref("");
const myArticles = ref([]);
const collections = ref([]);
const historyList = ref([]);
const readLaterList = ref([]);
const isUserLoading = ref(false);
const isArticlesLoading = ref(false);
const isCollectionsLoading = ref(false);
const isHistoryLoading = ref(false);
const isReadLaterLoading = ref(false);
const isSaving = ref(false);
const activeTab = ref("articles");
const showEditDialog = ref(false);

// 方案3: 编辑表单
const editForm = reactive({
  username: "",
  email: "",
  phone: "",
  bio: "",
});

// 方案4: 模拟近30天阅读活跃度数据
const activityData = ref([]);
const activityLabels = ref([]);

function generateActivityData() {
  const data = [];
  const labels = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    labels.push(`${d.getMonth() + 1}/${d.getDate()}`);
    // 基于阅读历史生成活跃度（简化：随机模拟）
    data.push(Math.floor(Math.random() * 5));
  }
  activityData.value = data;
  activityLabels.value = labels;
}

// Tab 懒加载追踪
const loadedTabs = new Set(["articles"]);

const preferenceTagList = computed(() => {
  return String(preferenceTags.value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
});

const profileInitial = computed(() => {
  const raw = String(userInfo.value?.username || userInfo.value?.email || "U").trim();
  return raw.charAt(0).toUpperCase();
});

const bubbleCloudStyle = computed(() => ({
  "--bubble-size": "108px",
  "--bubble-font-size": "15px",
  "--bubble-close-size": "24px",
  "--bubble-text-width": "80px",
}));

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).replace("T", " ").slice(0, 16);
}

function formatDepth(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

// 方案5: 从文章内容提取封面图
function extractCover(item) {
  const content = item.content || item.html_content || "";
  const mdMatch = content.match(/!\[[^\]]*\]\(([^)]+)\)/);
  if (mdMatch) return mdMatch[1];
  const htmlMatch = content.match(/<img\s+[^>]*src=["']([^"']+)["']/);
  if (htmlMatch) return htmlMatch[1];
  return null;
}

function syncTags(tags) {
  preferenceTags.value = Array.from(new Set(tags.map((item) => String(item).trim()).filter(Boolean))).join(",");
}

function addTag() {
  const value = String(newTag.value || "").trim();
  if (!value) return;
  if (preferenceTagList.value.includes(value)) {
    ElMessage.warning("该标签已存在");
    return;
  }
  syncTags([...preferenceTagList.value, value]);
  newTag.value = "";
}

function removeTag(tag) {
  syncTags(preferenceTagList.value.filter((item) => item !== tag));
}

async function loadUserInfo() {
  try {
    isUserLoading.value = true;
    const data = await fetchUserInfo();
    userInfo.value = data || null;
    preferenceTags.value = data?.preference_tags || "";
    setCachedUserInfo(data || {});
    // 同步编辑表单
    editForm.username = data?.username || "";
    editForm.email = data?.email || "";
    editForm.phone = data?.phone || "";
    editForm.bio = data?.bio || "";
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

async function loadCollections() {
  try {
    isCollectionsLoading.value = true;
    const data = await fetchCollections({ page: 1, page_size: 8 });
    collections.value = data?.list || [];
  } finally {
    isCollectionsLoading.value = false;
  }
}

async function loadHistory() {
  try {
    isHistoryLoading.value = true;
    const data = await fetchReadHistory({ page: 1, page_size: 8 });
    historyList.value = data?.list || [];
  } finally {
    isHistoryLoading.value = false;
  }
}

async function loadReadLaterList() {
  try {
    isReadLaterLoading.value = true;
    const data = await fetchReadLater({ page: 1, page_size: 8 });
    readLaterList.value = data?.list || [];
  } finally {
    isReadLaterLoading.value = false;
  }
}

// 方案1: Tab 切换时懒加载
function handleTabChange(tabName) {
  if (loadedTabs.has(tabName)) return;
  loadedTabs.add(tabName);
  if (tabName === "collections") loadCollections();
  if (tabName === "history") loadHistory();
  if (tabName === "readlater") loadReadLaterList();
}

async function savePreference() {
  try {
    isSaving.value = true;
    syncTags(preferenceTagList.value);
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

async function removeCollection(item) {
  await toggleCollect({ article_id: item.article_id, action: "uncollect" });
  ElMessage.success("已取消收藏");
  await Promise.all([loadCollections(), loadUserInfo()]);
}

async function removeReadLater(item) {
  await toggleReadLater({ article_id: item.article_id, action: "remove" });
  ElMessage.success("已移出稍后读");
  await Promise.all([loadReadLaterList(), loadUserInfo()]);
}

// 方案3: 保存个人资料
async function handleSaveProfile() {
  try {
    isSaving.value = true;
    await updateUserProfile({
      username: editForm.username,
      email: editForm.email,
      phone: editForm.phone,
      bio: editForm.bio,
    });
    ElMessage.success("资料更新成功");
    showEditDialog.value = false;
    await loadUserInfo(); // 刷新页面数据和缓存
  } catch (err) {
    ElMessage.error(err?.message || "更新失败，请重试");
  } finally {
    isSaving.value = false;
  }
}

onMounted(() => {
  loadUserInfo();
  loadMyArticles(); // 首屏只加载文章 tab
  generateActivityData();
});
</script>
