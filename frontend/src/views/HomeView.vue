<!--
  HomeView.vue —— 首页视图

  功能说明：
    - Hero 区：展示平台标语和快捷入口（浏览文章 / 开始创作）
    - 筛选区：支持关键词/分类/标签三维度搜索
    - 主内容区（左）：
        * 未搜索时：调用推荐接口（/recommend/list）展示个性化推荐
        * 搜索时：调用文章列表接口（/article/list）展示搜索结果
        * 支持"加载更多"分页（追加模式，不刷新整页）
    - 侧边栏（右）：热门文章列表（按热度排序的 Top 6）
    - 点赞功能：直接在列表卡片上点赞/取消点赞，并上报行为数据

  数据流：
    - 推荐列表：fetchRecommendList（登录用户个性化，未登录热度降级）
    - 搜索列表：fetchArticleList（带 keyword/category/tags 参数）
    - 热门列表：fetchArticleList（order="hottest"，固定 6 条）

  路由：/（公开页面，无需登录）
-->
<template>
  <!-- 使用通用应用布局（AppLayout 提供导航栏 + 内容区） -->
  <AppLayout>
    <!-- Hero 区：平台标语和快捷入口 -->
    <section class="hero-block">
      <p class="hero-kicker">Curated Reading</p>
      <h1 class="hero-title">从这里开始读今天值得看的内容</h1>
      <p class="hero-subtitle">
       你可以直接阅读推荐文章，也可以通过关键词、分类和标签快速筛选。
      </p>
      <div class="hero-actions">
        <router-link class="solid-button" to="/articles">浏览全部文章</router-link>
        <router-link class="ghost-button" to="/editor">开始创作</router-link>
      </div>
    </section>

    <!-- 筛选区：关键词/分类/标签三维度搜索 -->
    <SectionCard title="探索内容">
      <p class="section-intro">
        通过关键词、分类和标签快速切换推荐视角，筛选结果会直接作用于当前内容流。
      </p>
      <el-form class="filter-bar" label-position="top">
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索标题与正文关键词" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="filters.category" placeholder="如：技术、生活" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filters.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <!-- 搜索按钮：loading 状态防止重复点击 -->
        <el-button class="solid-button" :loading="isListLoading" @click="handleSearch">搜索</el-button>
      </el-form>
    </SectionCard>

    <!-- 主内容区：左侧文章列表 + 右侧热门侧边栏 -->
    <div class="home-grid">
      <!-- 左侧：个性化推荐 / 搜索结果 -->
      <SectionCard :title="isSearching ? '搜索结果' : '个性化推荐'">
        <template #actions>
          <span class="meta-text">{{ total }} 篇内容</span>
        </template>
        <!-- 加载骨架屏 -->
        <div v-if="isListLoading" class="skeleton-list">
          <div v-for="item in 4" :key="item" class="skeleton-line"></div>
        </div>
        <!-- 空状态 -->
        <div v-else-if="articleList.length === 0">
          <EmptyState title="暂无内容" message="尝试调整筛选条件。" />
        </div>
        <!-- 文章卡片列表 -->
        <div v-else class="card-list">
          <article v-for="item in articleList" :key="item.article_id" class="list-card">
            <!-- 文章元信息：分类标签 + 发布时间 -->
            <div class="list-card__meta">
              <span class="tag-chip">{{ item.category || "未分类" }}</span>
              <span class="meta-text">{{ formatDate(item.create_time) }}</span>
            </div>
            <h3 class="list-card__title">{{ item.title }}</h3>
            <p class="list-card__summary">{{ item.summary || "暂无摘要" }}</p>
            <!-- 标签列表：最多显示 4 个 -->
            <div v-if="item.tags?.length" class="tag-list">
              <span
                v-for="tag in item.tags.slice(0, 4)"
                :key="`${item.article_id}-${tag}`"
                class="tag-chip tag-chip--soft"
              >
                {{ tag }}
              </span>
            </div>
            <!-- 统计数据：阅读量/点赞数/评论数 -->
            <div class="list-card__stats">
              <span class="list-stat">阅读 {{ item.view_count || 0 }}</span>
              <span class="list-stat">点赞 {{ item.like_count || 0 }}</span>
              <span class="list-stat">评论 {{ item.comment_count || 0 }}</span>
            </div>
            <!-- 卡片底部：作者信息 + 操作按钮 -->
            <div class="list-card__footer">
              <span class="meta-text">作者：{{ item.author?.username || "匿名" }}</span>
              <div class="list-actions list-actions--aligned">
                <!-- 点赞按钮：点击切换点赞状态并上报行为 -->
                <el-button class="ghost-button ghost-button--compact" @click="handleLike(item)">
                  赞 {{ item.like_count || 0 }}
                </el-button>
                <!-- 阅读按钮：跳转到文章详情页 -->
                <router-link class="ghost-button ghost-button--compact" :to="`/articles/${item.article_id}`">
                  阅读
                </router-link>
              </div>
            </div>
          </article>
        </div>
        <!-- 加载更多按钮：已加载全部时禁用 -->
        <div class="mt-6 flex items-center justify-center">
          <el-button
            class="ghost-button"
            :disabled="articleList.length >= total"
            :loading="isLoadingMore"
            @click="loadMore"
          >
            加载更多
          </el-button>
        </div>
      </SectionCard>

      <!-- 右侧侧边栏：热门文章 Top 6 -->
      <div class="sidebar-stack">
        <SectionCard title="热门文章">
          <!-- 加载骨架屏 -->
          <div v-if="isHotLoading" class="skeleton-list">
            <div v-for="item in 4" :key="item" class="skeleton-line"></div>
          </div>
          <div v-else-if="hotList.length === 0">
            <EmptyState title="暂无热门" message="稍后再试" />
          </div>
          <!-- 热门文章列表：点击跳转到文章详情页 -->
          <div v-else class="stack-list">
            <router-link
              v-for="item in hotList"
              :key="item.article_id"
              class="stack-item"
              :to="`/articles/${item.article_id}`"
            >
              <p class="stack-title">{{ item.title }}</p>
              <p class="stack-description">按阅读热度聚合，适合快速查看站内热点。</p>
              <div class="stack-meta">
                <span class="meta-text">{{ item.category || "未分类" }}</span>
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
/**
 * HomeView 脚本逻辑
 *
 * 响应式状态：
 *   - filters       : 搜索筛选条件（keyword/category/tags）
 *   - page          : 当前页码（加载更多时递增）
 *   - total         : 文章总数（用于判断是否还有更多）
 *   - articleList   : 主内容区文章列表（追加模式）
 *   - hotList       : 侧边栏热门文章列表
 *   - isListLoading : 主列表加载中标志（首次加载/搜索时）
 *   - isLoadingMore : 加载更多中标志
 *   - isHotLoading  : 热门列表加载中标志
 *   - isSearching   : 计算属性，是否处于搜索状态（任一筛选条件非空）
 */
import { computed, onMounted, reactive, ref } from "vue";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { fetchArticleList, toggleLike } from "../services/article.js";
import { fetchRecommendList } from "../services/recommend.js";
import { trackLike, trackSearch } from "../services/behavior.js";

// 搜索筛选条件
const filters = reactive({
  keyword: "",   // 关键词（模糊匹配标题/正文）
  category: "",  // 分类（精确匹配）
  tags: "",      // 标签（逗号分隔，模糊匹配）
});

const page = ref(1);           // 当前页码
const pageSize = 6;            // 每页文章数（固定值）
const total = ref(0);          // 文章总数
const articleList = ref([]);   // 主内容区文章列表
const hotList = ref([]);       // 侧边栏热门文章列表
const isListLoading = ref(false);   // 主列表加载中（首次/搜索）
const isLoadingMore = ref(false);   // 加载更多中
const isHotLoading = ref(false);    // 热门列表加载中

/**
 * 计算属性：是否处于搜索状态。
 * 任一筛选条件非空时为 true，影响：
 *   - 主内容区标题（"搜索结果" vs "个性化推荐"）
 *   - 数据来源（fetchArticleList vs fetchRecommendList）
 */
const isSearching = computed(() => {
  return Boolean(filters.keyword.trim() || filters.category.trim() || filters.tags.trim());
});

/**
 * 格式化日期字符串，只保留日期部分（去掉时间）。
 * @param {string} value - 日期时间字符串（如 "2024-01-15 10:30:00"）
 * @returns {string} 日期字符串（如 "2024-01-15"）
 */
function formatDate(value) {
  if (!value) return "未知时间";
  return String(value).split(" ")[0];  // 取空格前的日期部分
}

/**
 * 加载文章列表（支持重置和追加两种模式）。
 *
 * @param {boolean} resetPage - true：重置到第 1 页（搜索/首次加载）；false：追加下一页（加载更多）
 *
 * 数据来源选择：
 *   - isSearching=true：调用 fetchArticleList（带筛选参数）
 *   - isSearching=false：调用 fetchRecommendList（个性化推荐）
 */
async function loadArticleList(resetPage) {
  if (resetPage) {
    page.value = 1;
    articleList.value = [];  // 重置列表
  }
  // 根据是否重置选择不同的 loading 标志
  const loadingFlag = resetPage ? isListLoading : isLoadingMore;
  try {
    loadingFlag.value = true;
    const data = isSearching.value
      ? await fetchArticleList({
          page: page.value,
          page_size: pageSize,
          category: filters.category || undefined,
          tags: filters.tags || undefined,
          keyword: filters.keyword || undefined,
          order: "latest",  // 搜索结果按最新排序
        })
      : await fetchRecommendList({
          page: page.value,
          page_size: pageSize,
        });
    const list = data?.list || [];
    total.value = data?.total || 0;
    // 重置模式：替换列表；追加模式：合并列表
    articleList.value = resetPage ? list : [...articleList.value, ...list];
  } finally {
    loadingFlag.value = false;
  }
}

/**
 * 加载热门文章列表（侧边栏，固定 6 条，按热度排序）。
 */
async function loadHotList() {
  try {
    isHotLoading.value = true;
    const data = await fetchArticleList({ page: 1, page_size: 6, order: "hottest" });
    hotList.value = data?.list || [];
  } finally {
    isHotLoading.value = false;
  }
}

/**
 * 处理搜索操作。
 * 上报搜索行为（用于热搜统计），然后重置并加载搜索结果。
 */
async function handleSearch() {
  trackSearch(filters.keyword);  // 上报搜索行为（用于热搜关键词统计）
  await loadArticleList(true);   // 重置页码并加载搜索结果
}

/**
 * 加载更多文章（追加模式）。
 * 已加载全部时直接返回，否则页码 +1 并追加加载。
 */
async function loadMore() {
  if (articleList.value.length >= total.value) return;  // 已加载全部，不再请求
  page.value += 1;
  await loadArticleList(false);  // 追加模式
}

/**
 * 处理文章点赞/取消点赞。
 *
 * 乐观更新：先调用 API，再用返回值更新本地状态。
 * 点赞成功后上报行为数据（用于推荐系统训练）。
 *
 * @param {Object} item - 文章列表项（含 article_id/is_liked/like_count）
 */
async function handleLike(item) {
  const action = item.is_liked ? "unlike" : "like";  // 根据当前状态决定操作
  const data = await toggleLike({ article_id: item.article_id, action });
  // 用服务端返回值更新本地状态（保证数据一致性）
  item.like_count = data?.like_count ?? item.like_count;
  item.is_liked = data?.is_liked ?? !item.is_liked;
  if (action === "like") {
    trackLike(item.article_id);  // 上报点赞行为（用于推荐系统）
  }
}

// 页面挂载时并行加载推荐列表和热门列表
onMounted(() => {
  loadArticleList(true);  // 加载个性化推荐（或热度降级）
  loadHotList();          // 加载热门文章侧边栏
});
</script>
