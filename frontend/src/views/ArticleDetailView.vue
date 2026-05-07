<template>
  <AppLayout>
    <div class="detail-grid">
      <div class="detail-main">
        <SectionCard>
          <div v-if="isLoading" class="skeleton-list">
            <div v-for="item in 5" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="!article">
            <EmptyState title="文章不存在" message="请返回列表重新选择文章。" />
          </div>
          <div v-else>
            <div class="detail-meta">
              <span class="tag-chip">{{ article.category || "未分类" }}</span>
              <span class="meta-text">{{ formatDate(article.create_time) }}</span>
              <span v-if="article.status" class="tag-chip tag-chip--soft">{{ article.status }}</span>
            </div>
            <h1 class="detail-title">{{ article.title }}</h1>
            <div class="detail-author">
              <span class="meta-text">作者：{{ article.author?.username || "匿名" }}</span>
              <span class="meta-divider"></span>
              <span class="meta-text">关注者 {{ article.author?.follower_count || 0 }}</span>
              <span class="meta-divider"></span>
              <span class="meta-text">阅读 {{ article.view_count || 0 }}</span>
              <span class="meta-divider"></span>
              <span class="meta-text">评论 {{ article.comment_count || 0 }}</span>
              <span class="meta-divider"></span>
              <span class="meta-text">收藏 {{ article.collect_count || 0 }}</span>
            </div>

            <div v-if="showFollowAuthorButton" class="mb-5">
              <el-button class="ghost-button" :loading="isFollowingAuthor" @click="handleFollowAuthor">
                {{ article.author?.is_followed ? "已关注作者" : "关注作者" }}
              </el-button>
            </div>

            <div v-if="article.tags?.length" class="tag-list">
              <span v-for="tag in article.tags" :key="`detail-${tag}`" class="tag-chip tag-chip--soft">
                {{ tag }}
              </span>
            </div>

            <div class="detail-kpi-grid">
              <div class="detail-kpi">
                <span class="detail-kpi__label">阅读数</span>
                <strong class="detail-kpi__value">{{ article.view_count || 0 }}</strong>
              </div>
              <div class="detail-kpi">
                <span class="detail-kpi__label">点赞数</span>
                <strong class="detail-kpi__value">{{ article.like_count || 0 }}</strong>
              </div>
              <div class="detail-kpi">
                <span class="detail-kpi__label">收藏数</span>
                <strong class="detail-kpi__value">{{ article.collect_count || 0 }}</strong>
              </div>
              <div class="detail-kpi">
                <span class="detail-kpi__label">评论数</span>
                <strong class="detail-kpi__value">{{ article.comment_count || 0 }}</strong>
              </div>
            </div>

            <div class="detail-actions">
              <el-button class="ghost-button" @click="handleLike">
                {{ article.is_liked ? "已点赞" : "点赞" }} ({{ article.like_count || 0 }})
              </el-button>
              <el-button class="ghost-button" @click="handleCollect">
                {{ article.is_collected ? "已收藏" : "收藏" }} ({{ article.collect_count || 0 }})
              </el-button>
              <el-button class="ghost-button" @click="handleReadLater">
                {{ article.is_saved_for_later ? "已加入稍后读" : "加入稍后读" }}
              </el-button>
            </div>

            <div class="detail-content" v-html="article.html_content || article.content"></div>
          </div>
        </SectionCard>

        <SectionCard title="评论区">
          <p class="section-intro">优先显示一级评论，并支持楼中回复，适合围绕文章主题继续展开讨论。</p>
          <el-form class="comment-form" label-position="top">
            <el-form-item label="发表评论">
              <el-input
                v-model="commentContent"
                type="textarea"
                :rows="3"
                placeholder="写下你的看法"
              />
            </el-form-item>
            <el-button class="solid-button" :loading="isSubmitting" @click="submitRootComment">
              发布评论
            </el-button>
          </el-form>

          <div v-if="isCommentLoading" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="topLevelComments.length === 0">
            <EmptyState title="暂无评论" message="成为第一个留言的人。" />
          </div>
          <div v-else class="comment-list">
            <div v-for="item in topLevelComments" :key="item.comment_id" class="comment-item">
              <p class="comment-author">{{ item.user?.username || "匿名用户" }}</p>
              <p class="comment-content">{{ item.content }}</p>
              <div class="comment-toolbar">
                <span class="meta-text">{{ formatDate(item.create_time) }}</span>
                <button type="button" class="comment-reply-link" @click="toggleReply(item.comment_id)">
                  {{ activeReplyId === item.comment_id ? "取消回复" : "回复" }}
                </button>
              </div>

              <div v-if="activeReplyId === item.comment_id" class="reply-editor">
                <el-input
                  v-model="replyDrafts[item.comment_id]"
                  type="textarea"
                  :rows="2"
                  placeholder="回复这条评论"
                />
                <div class="reply-editor__actions">
                  <el-button
                    class="solid-button"
                    size="small"
                    :loading="replySubmittingId === item.comment_id"
                    @click="submitReply(item.comment_id)"
                  >
                    发送回复
                  </el-button>
                </div>
              </div>

              <div v-if="item.replies.length" class="reply-list">
                <div
                  v-for="reply in item.replies"
                  :key="reply.comment_id"
                  class="comment-item comment-item--reply"
                >
                  <p class="comment-author">{{ reply.user?.username || "匿名用户" }}</p>
                  <p class="comment-content">{{ reply.content }}</p>
                  <span class="meta-text">{{ formatDate(reply.create_time) }}</span>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      <div class="detail-side">
        <SectionCard title="阅读信息">
          <div v-if="article" class="detail-side-list">
            <div class="detail-side-item">
              <span class="detail-side-label">作者</span>
              <span class="detail-side-value">{{ article.author?.username || "匿名" }}</span>
            </div>
            <div class="detail-side-item">
              <span class="detail-side-label">分类</span>
              <span class="detail-side-value">{{ article.category || "未分类" }}</span>
            </div>
            <div class="detail-side-item">
              <span class="detail-side-label">发布时间</span>
              <span class="detail-side-value">{{ formatDate(article.create_time) }}</span>
            </div>
            <div class="detail-side-item">
              <span class="detail-side-label">更新时间</span>
              <span class="detail-side-value">{{ formatDate(article.update_time) }}</span>
            </div>
          </div>
          <div v-else class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
        </SectionCard>

        <SectionCard title="相关文章">
          <div v-if="isSimilarLoading" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="similarList.length === 0">
            <EmptyState title="暂无推荐" message="稍后再试。" />
          </div>
          <div v-else class="stack-list">
            <router-link
              v-for="item in similarList"
              :key="item.article_id"
              class="stack-item"
              :to="`/articles/${item.article_id}`"
            >
              <p class="stack-title">{{ item.title }}</p>
              <p class="stack-description">基于内容相似度与标签关系做推荐。</p>
              <div class="stack-meta">
                <span class="meta-text">{{ formatDate(item.create_time) }}</span>
                <span class="meta-text">阅读 {{ item.view_count || 0 }}</span>
              </div>
            </router-link>
          </div>
        </SectionCard>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { fetchArticleDetail, toggleCollect, toggleLike } from "../services/article.js";
import { fetchSimilarArticles } from "../services/recommend.js";
import { fetchCommentList, submitComment } from "../services/comment.js";
import { trackCollect, trackComment, trackLike, trackRead } from "../services/behavior.js";
import { toggleReadLater } from "../services/library.js";
import { toggleFollow } from "../services/social.js";
import { getCachedUserInfo, refreshCurrentUserInfo } from "../services/user.js";

const route = useRoute();
const article = ref(null);
const similarList = ref([]);
const comments = ref([]);
const commentContent = ref("");
const activeReplyId = ref(null);
const replySubmittingId = ref(null);
const replyDrafts = reactive({});
const isLoading = ref(false);
const isSimilarLoading = ref(false);
const isCommentLoading = ref(false);
const isSubmitting = ref(false);
const isFollowingAuthor = ref(false);
const readStartTime = ref(0);
const maxScrollDepth = ref(0);

const topLevelComments = computed(() => {
  const replyMap = new Map();
  const roots = [];

  for (const item of comments.value) {
    if (!item.parent_id) {
      roots.push({ ...item, replies: [] });
      continue;
    }
    if (!replyMap.has(item.parent_id)) {
      replyMap.set(item.parent_id, []);
    }
    replyMap.get(item.parent_id).push(item);
  }

  return roots.map((item) => ({
    ...item,
    replies: replyMap.get(item.comment_id) || [],
  }));
});

const showFollowAuthorButton = computed(() => {
  const currentUserId = Number(getCachedUserInfo()?.user_id || 0);
  if (!article.value?.author?.user_id || !currentUserId) return false;
  return article.value.author.user_id !== currentUserId;
});

function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).replace("T", " ").slice(0, 16);
}

async function loadArticleDetail() {
  try {
    isLoading.value = true;
    const data = await fetchArticleDetail(route.params.id);
    article.value = data || null;
  } finally {
    isLoading.value = false;
  }
}

async function loadSimilarArticles() {
  try {
    isSimilarLoading.value = true;
    const data = await fetchSimilarArticles({
      article_id: route.params.id,
      size: 5,
    });
    similarList.value = data?.list || [];
  } finally {
    isSimilarLoading.value = false;
  }
}

async function loadComments() {
  try {
    isCommentLoading.value = true;
    const data = await fetchCommentList({
      article_id: route.params.id,
      page: 1,
      page_size: 50,
    });
    comments.value = data?.list || [];
  } finally {
    isCommentLoading.value = false;
  }
}

async function submitRootComment() {
  if (!commentContent.value.trim()) return;
  try {
    isSubmitting.value = true;
    await submitComment({
      article_id: route.params.id,
      content: commentContent.value.trim(),
      parent_id: 0,
    });
    commentContent.value = "";
    if (article.value) {
      article.value.comment_count = (article.value.comment_count || 0) + 1;
      trackComment(article.value.article_id);
    }
    await loadComments();
  } finally {
    isSubmitting.value = false;
  }
}

function toggleReply(commentId) {
  activeReplyId.value = activeReplyId.value === commentId ? null : commentId;
}

async function submitReply(commentId) {
  const content = String(replyDrafts[commentId] || "").trim();
  if (!content) {
    ElMessage.warning("请输入回复内容");
    return;
  }
  try {
    replySubmittingId.value = commentId;
    await submitComment({
      article_id: route.params.id,
      content,
      parent_id: commentId,
    });
    replyDrafts[commentId] = "";
    activeReplyId.value = null;
    if (article.value) {
      article.value.comment_count = (article.value.comment_count || 0) + 1;
      trackComment(article.value.article_id);
    }
    await loadComments();
  } finally {
    replySubmittingId.value = null;
  }
}

async function handleLike() {
  if (!article.value) return;
  const action = article.value.is_liked ? "unlike" : "like";
  const data = await toggleLike({
    article_id: article.value.article_id,
    action,
  });
  article.value.like_count = data?.like_count ?? article.value.like_count;
  article.value.is_liked = data?.is_liked ?? !article.value.is_liked;
  if (action === "like") {
    trackLike(article.value.article_id);
  }
}

async function handleCollect() {
  if (!article.value) return;
  const action = article.value.is_collected ? "uncollect" : "collect";
  const data = await toggleCollect({
    article_id: article.value.article_id,
    action,
  });
  article.value.collect_count = data?.collect_count ?? article.value.collect_count;
  article.value.is_collected = data?.is_collected ?? !article.value.is_collected;
  if (action === "collect") {
    trackCollect(article.value.article_id);
  }
  await refreshCurrentUserInfo();
}

async function handleReadLater() {
  if (!article.value) return;
  const action = article.value.is_saved_for_later ? "remove" : "save";
  const data = await toggleReadLater({
    article_id: article.value.article_id,
    action,
  });
  article.value.is_saved_for_later = Boolean(data?.is_saved_for_later);
  await refreshCurrentUserInfo();
}

async function handleFollowAuthor() {
  if (!article.value?.author?.user_id) return;
  try {
    isFollowingAuthor.value = true;
    const action = article.value.author.is_followed ? "unfollow" : "follow";
    const data = await toggleFollow({
      target_user_id: article.value.author.user_id,
      action,
    });
    article.value.author.is_followed = Boolean(data?.is_followed);
    article.value.author.follower_count = Number(
      data?.follower_count ?? article.value.author.follower_count ?? 0
    );
    await refreshCurrentUserInfo();
  } finally {
    isFollowingAuthor.value = false;
  }
}

function handleScroll() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
  const depth = scrollHeight > 0 ? scrollTop / scrollHeight : 0;
  if (depth > maxScrollDepth.value) {
    maxScrollDepth.value = depth;
  }
}

async function reportReadBehavior() {
  if (!article.value) return;
  const duration = Math.round((Date.now() - readStartTime.value) / 1000);
  trackRead({
    articleId: article.value.article_id,
    duration,
    scrollDepth: maxScrollDepth.value,
  });
}

onMounted(() => {
  readStartTime.value = Date.now();
  window.addEventListener("scroll", handleScroll, { passive: true });
  loadArticleDetail();
  loadSimilarArticles();
  loadComments();
});

onBeforeUnmount(() => {
  window.removeEventListener("scroll", handleScroll);
  reportReadBehavior();
});
</script>
