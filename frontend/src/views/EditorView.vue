<template>
  <AppLayout>
    <SectionCard :title="pageTitle">
      <el-form class="editor-form" label-position="top">
        <el-form-item label="文章封面/插图">
          <div class="upload-card">
            <el-upload
              action="/api/upload/image"
              :headers="uploadHeaders"
              :show-file-list="false"
              :before-upload="validateUpload"
              :on-success="handleUploadSuccess"
              accept="image/*"
            >
              <el-button class="ghost-button">上传图片</el-button>
            </el-upload>
            <p class="upload-hint">支持 PNG/JPG/WebP，上传后自动插入 Markdown。</p>
          </div>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="输入文章标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="例如：技术/生活" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="以逗号分隔多个标签" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="选择状态">
            <el-option label="已发布" value="published" />
            <el-option label="草稿" value="draft" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input
            ref="contentRef"
            v-model="form.content"
            type="textarea"
            :rows="10"
            placeholder="支持 Markdown 格式内容"
          />
        </el-form-item>
        <div class="flex flex-wrap gap-3">
          <el-button class="solid-button" :loading="isSubmitting" @click="handleSubmit">
            {{ isEditing ? "保存更新" : "发布文章" }}
          </el-button>
          <el-button class="ghost-button" @click="resetForm">重置内容</el-button>
        </div>
      </el-form>
    </SectionCard>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import AppLayout from "../components/AppLayout.vue";
import SectionCard from "../components/SectionCard.vue";
import { editArticle, fetchArticleDetail, publishArticle } from "../services/article.js";
import { getAuthToken } from "../services/http.js";

const route = useRoute();
const isSubmitting = ref(false);
const contentRef = ref(null);
const form = reactive({
  title: "",
  category: "",
  tags: "",
  status: "published",
  content: "",
});

const uploadHeaders = computed(() => {
  const token = getAuthToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
});

/**
 * Determine whether the editor is in edit mode.
 * @returns {boolean} True when editing an existing article.
 */
function resolveIsEditing() {
  return Boolean(route.params.id);
}

/**
 * Resolve editor page title based on mode.
 * @returns {string} Page title text.
 */
function resolvePageTitle() {
  return resolveIsEditing() ? "编辑文章" : "发布文章";
}

const isEditing = computed(resolveIsEditing);
const pageTitle = computed(resolvePageTitle);

/**
 * Populate editor form from article detail.
 * @returns {Promise<void>} No return value.
 */
async function loadArticle() {
  if (!isEditing.value) return;
  const data = await fetchArticleDetail(route.params.id);
  form.title = data?.title || "";
  form.category = data?.category || "";
  form.tags = Array.isArray(data?.tags) ? data.tags.join(",") : data?.tags || "";
  form.status = data?.status || "published";
  form.content = data?.content || "";
}

/**
 * Validate image upload before sending to server.
 * @param {File} file Selected file.
 * @returns {boolean} True when the file is accepted.
 */
function validateUpload(file) {
  const isImage = file.type.startsWith("image/");
  if (!isImage) {
    ElMessage.warning("仅支持上传图片文件。");
    return false;
  }
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    ElMessage.warning("图片大小不能超过 5MB。");
    return false;
  }
  return true;
}

/**
 * Insert markdown image into editor content.
 * @param {string} url Uploaded image URL.
 * @returns {void} No return value.
 */
function insertImageMarkdown(url) {
  const markdown = `\n\n![](${url})\n\n`;
  const textarea = contentRef.value?.textarea || contentRef.value?.input;
  if (!textarea) {
    form.content = `${form.content}${markdown}`;
    return;
  }
  const start = textarea.selectionStart ?? form.content.length;
  const end = textarea.selectionEnd ?? form.content.length;
  const current = form.content;
  form.content = `${current.slice(0, start)}${markdown}${current.slice(end)}`;
  requestAnimationFrame(() => {
    const cursor = start + markdown.length;
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
  });
}

/**
 * Handle successful image upload response.
 * @param {any} response Upload response payload.
 * @returns {void} No return value.
 */
function handleUploadSuccess(response) {
  const url = response?.data?.url || response?.url || response?.data?.file_url;
  if (!url) {
    ElMessage.warning("未获取到图片地址，请重试。");
    return;
  }
  insertImageMarkdown(url);
  ElMessage.success("图片已插入到正文。");
}

/**
 * Reset editor form to default values.
 * @returns {void} No return value.
 */
function resetForm() {
  form.title = "";
  form.category = "";
  form.tags = "";
  form.status = "published";
  form.content = "";
}

/**
 * Submit article publish or edit request.
 * @returns {Promise<void>} No return value.
 */
async function handleSubmit() {
  if (!form.title.trim() || !form.category.trim() || !form.content.trim()) {
    ElMessage.warning("请完善标题、分类与正文内容。");
    return;
  }
  try {
    isSubmitting.value = true;
    const payload = {
      title: form.title.trim(),
      category: form.category.trim(),
      tags: form.tags.trim(),
      status: form.status,
      content: form.content.trim(),
    };
    if (isEditing.value) {
      await editArticle({
        ...payload,
        article_id: route.params.id,
      });
      ElMessage.success("文章已更新。");
    } else {
      await publishArticle(payload);
      ElMessage.success("文章已发布。");
      resetForm();
    }
  } finally {
    isSubmitting.value = false;
  }
}

/**
 * Initialize editor data loading.
 * @returns {void} No return value.
 */
function handleMounted() {
  loadArticle();
}

onMounted(handleMounted);
</script>
