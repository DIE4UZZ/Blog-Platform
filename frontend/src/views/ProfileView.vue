<template>
  <AppLayout>
    <div class="profile-grid profile-grid--hero">
      <SectionCard title="个人概览">
        <div v-if="isUserLoading" class="skeleton-list">
          <div v-for="item in 3" :key="item" class="skeleton-line"></div>
        </div>
        <div v-else-if="!userInfo">
          <EmptyState title="暂无用户信息" message="请先登录" />
        </div>
        <div v-else class="profile-hero">
          <div class="profile-hero__main">
            <div class="profile-avatar">{{ profileInitial }}</div>
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

          <div class="profile-highlight-grid">
            <div class="profile-highlight">
              <span class="profile-highlight__label">加入时间</span>
              <strong class="profile-highlight__value">{{ formatDate(userInfo.create_time) }}</strong>
            </div>
            <div class="profile-highlight">
              <span class="profile-highlight__label">兴趣标签</span>
              <strong class="profile-highlight__value">{{ preferenceTagList.length }}</strong>
            </div>
            <div class="profile-highlight">
              <span class="profile-highlight__label">文章数量</span>
              <strong class="profile-highlight__value">{{ myArticles.length }}</strong>
            </div>
            <div class="profile-highlight">
              <span class="profile-highlight__label">关注中</span>
              <strong class="profile-highlight__value">{{ userInfo.following_count || 0 }}</strong>
            </div>
            <div class="profile-highlight">
              <span class="profile-highlight__label">关注者</span>
              <strong class="profile-highlight__value">{{ userInfo.follower_count || 0 }}</strong>
            </div>
            <div class="profile-highlight">
              <span class="profile-highlight__label">未读通知</span>
              <strong class="profile-highlight__value">{{ userInfo.unread_notification_count || 0 }}</strong>
            </div>
          </div>
        </div>
      </SectionCard>

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
    </div>

    <SectionCard title="我的文章">
      <template #actions>
        <router-link class="ghost-button" to="/editor">写新文章</router-link>
      </template>
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
              <router-link class="ghost-button ghost-button--compact" :to="`/editor/${item.article_id}`">
                编辑
              </router-link>
              <button type="button" class="ghost-button ghost-button--danger" @click="removeArticle(item)">
                删除
              </button>
            </div>
          </div>
        </article>
      </div>
    </SectionCard>

    <SectionCard title="我的收藏">
      <div v-if="isCollectionsLoading" class="skeleton-list">
        <div v-for="item in 3" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="collections.length === 0">
        <EmptyState title="还没有收藏文章" message="看到喜欢的文章后，可以在详情页加入收藏。" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in collections" :key="item.article_id" class="list-card">
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
              <button type="button" class="ghost-button ghost-button--danger" @click="removeCollection(item)">
                取消收藏
              </button>
            </div>
          </div>
        </article>
      </div>
    </SectionCard>

    <SectionCard title="阅读历史">
      <div v-if="isHistoryLoading" class="skeleton-list">
        <div v-for="item in 3" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="historyList.length === 0">
        <EmptyState title="暂无阅读历史" message="开始阅读文章后，这里会自动沉淀你的访问记录。" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in historyList" :key="item.article_id" class="list-card">
          <div class="list-card__meta">
            <span class="tag-chip">{{ item.category || "未分类" }}</span>
            <span class="meta-text">最近阅读 {{ formatDate(item.last_read_time) }}</span>
          </div>
          <h3 class="list-card__title">{{ item.title }}</h3>
          <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
          <div class="list-card__stats">
            <span class="list-stat">阅读次数 {{ item.read_count || 0 }}</span>
            <span class="list-stat">时长 {{ item.last_read_duration || 0 }}s</span>
            <span class="list-stat">滚动 {{ formatDepth(item.max_scroll_depth) }}</span>
          </div>
          <div class="list-card__footer">
            <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
            <router-link class="text-link" :to="`/articles/${item.article_id}`">继续阅读</router-link>
          </div>
        </article>
      </div>
    </SectionCard>

    <SectionCard title="稍后读">
      <div v-if="isReadLaterLoading" class="skeleton-list">
        <div v-for="item in 3" :key="item" class="skeleton-line"></div>
      </div>
      <div v-else-if="readLaterList.length === 0">
        <EmptyState title="稍后读列表为空" message="可以把还没来得及细读的文章先存起来。" />
      </div>
      <div v-else class="card-list">
        <article v-for="item in readLaterList" :key="item.article_id" class="list-card">
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
              <button type="button" class="ghost-button ghost-button--danger" @click="removeReadLater(item)">
                移出列表
              </button>
            </div>
          </div>
        </article>
      </div>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { deleteArticle, fetchMyArticles, toggleCollect } from "../services/article.js";
import { fetchCollections, fetchReadHistory, fetchReadLater, toggleReadLater } from "../services/library.js";
import { fetchUserInfo, setCachedUserInfo, updatePreferenceTags } from "../services/user.js";

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

onMounted(() => {
  loadUserInfo();
  loadMyArticles();
  loadCollections();
  loadHistory();
  loadReadLaterList();
});
</script>
