<template>
  <AppLayout>
    <div class="detail-grid">
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
          </div>
          <h1 class="detail-title">{{ article.title }}</h1>
          <div class="detail-author">
            <span class="meta-text">作者：{{ article.author?.username || "匿名" }}</span>
            <span class="meta-divider"></span>
            <span class="meta-text">阅读 {{ article.view_count || 0 }}</span>
            <span class="meta-divider"></span>
            <span class="meta-text">评论 {{ article.comment_count || 0 }}</span>
          </div>
          <div class="detail-actions">
            <el-button class="ghost-button" @click="handleLike">
              {{ article.is_liked ? "已点赞" : "点赞" }} ({{ article.like_count || 0 }})
            </el-button>
            <el-button class="ghost-button" @click="handleCollect">
              {{ article.is_collected ? "已收藏" : "收藏" }} ({{ article.collect_count || 0 }})
            </el-button>
          </div>
          <div class="detail-content" v-html="article.html_content || article.content"></div>
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
            <span class="meta-text">{{ formatDate(item.create_time) }}</span>
          </router-link>
        </div>
      </SectionCard>
    </div>

    <SectionCard title="评论区">
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

/**
 * 格式化时间字符串。
 * @param {string} value 时间值。
 * @returns {string} 格式化后的日期。
 */
function formatDate(value) {
  if (!value) return "未知时间";
  return value.split(" ")[0];
}

/**
 * 加载文章详情。
 * @returns {Promise<void>} 无返回值。
 */
async function loadArticleDetail() {
  try {
    isLoading.value = true;
    const data = await fetchArticleDetail(route.params.id);
    article.value = data || null;
  } finally {
    isLoading.value = false;
  }
}

/**
 * 加载相关文章推荐。
 * @returns {Promise<void>} 无返回值。
 */
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

/**
 * 加载评论列表。
 * @returns {Promise<void>} 无返回值。
 */
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

/**
 * 提交一级评论。
 * @returns {Promise<void>} 无返回值。
 */
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

/**
 * 切换回复输入框显示状态。
 * @param {number} commentId 评论 ID。
 * @returns {void} 无返回值。
 */
function toggleReply(commentId) {
  activeReplyId.value = activeReplyId.value === commentId ? null : commentId;
}

/**
 * 提交评论回复。
 * @param {number} commentId 父评论 ID。
 * @returns {Promise<void>} 无返回值。
 */
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

/**
 * 切换文章点赞状态。
 * @returns {Promise<void>} 无返回值。
 */
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

/**
 * 切换文章收藏状态。
 * @returns {Promise<void>} 无返回值。
 */
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
}

/**
 * 记录最大滚动深度。
 * @returns {void} 无返回值。
 */
function handleScroll() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
  const depth = scrollHeight > 0 ? scrollTop / scrollHeight : 0;
  if (depth > maxScrollDepth.value) {
    maxScrollDepth.value = depth;
  }
}

/**
 * 上报阅读行为。
 * @returns {Promise<void>} 无返回值。
 */
async function reportReadBehavior() {
  if (!article.value) return;
  const duration = Math.round((Date.now() - readStartTime.value) / 1000);
  trackRead({
    articleId: article.value.article_id,
    duration,
    scrollDepth: maxScrollDepth.value,
  });
}

/**
 * 初始化页面数据。
 * @returns {void} 无返回值。
 */
function handleMounted() {
  readStartTime.value = Date.now();
  window.addEventListener("scroll", handleScroll, { passive: true });
  loadArticleDetail();
  loadSimilarArticles();
  loadComments();
}

/**
 * 页面卸载时清理监听并上报行为。
 * @returns {void} 无返回值。
 */
function handleBeforeUnmount() {
  window.removeEventListener("scroll", handleScroll);
  reportReadBehavior();
}

onMounted(handleMounted);
onBeforeUnmount(handleBeforeUnmount);
</script>
