# ALIGNMENT_frontend-core

## 任务概述
在现有 Vue3 前端工程基础上，完成博客平台剩余核心页面的前端实现，包括首页推荐流、文章列表/分类/搜索、文章详情（含互动与相似推荐）、文章发布/编辑、个人中心（偏好标签与我的文章）、数据分析仪表盘。

## 已知资料
- 需求文档：`需求文档.md`
- API 文档：`API.md`
- 规则：`rules/5S.md`、`rules/6A.md`
- 现有工程：`frontend/`（Vue3 + Tailwind + Element Plus + Axios）

## 任务范围（In Scope）
- 完整页面与路由：`/`、`/articles`、`/articles/:id`、`/editor`、`/editor/:id`、`/profile`、`/analysis`
- API 对接：文章、推荐、互动、评论、用户信息、偏好标签、数据分析
- UI 统一：现代简约、Apple 风格、响应式布局
- 交互与状态：加载、错误提示、表单校验、空状态

## 非范围（Out of Scope）
- 后端接口实现与数据库
- 权限管理的高级流程

## 风险与不确定性
- 后端接口字段与分页格式若有调整需同步更新
- 数据分析接口可能返回结构有变化

## 待确认点
- 是否需要登录态强制跳转（如未登录访问 editor/profile/analysis）
- 文章内容编辑是否要求 Markdown 编辑器（当前仅提供简单输入框）

## 下一步
- 生成 CONSENSUS 与 DESIGN 文档，进入模块设计与实现。
