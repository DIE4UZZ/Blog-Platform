# ALIGNMENT_leaderboard

## 任务概述
基于排行榜模块截图，新增博客平台排行榜页面与配套接口，包含榜单列表、热搜词、推荐关注三块内容，先完成前端页面与交互，再补齐后端数据接口。

## 已知资料
- 需求文档：`需求文档.md`
- API 文档：`API.md`
- 规则：`rules/5S.md`、`rules/6A.md`
- 前端：`frontend/`（Vue3 + Element Plus + Axios + Tailwind 样式）
- 后端：`backend/`（FastAPI + SQLAlchemy + MySQL）

## 任务范围（In Scope）
- 前端新增排行榜页面与组件（榜单列表、热搜卡片、推荐关注卡片）
- 新增前端服务层接口封装（排行榜列表、热搜、推荐关注）
- 后端新增排行榜相关 API（/rank/list、/rank/hot-search、/rank/recommend）
- 与现有 AppLayout/SectionCard 视觉风格保持一致

## 非范围（Out of Scope）
- 新的推荐算法/模型训练
- 运营后台、内容审核流程
- 登录/注册/权限体系重构

## 风险与不确定性
- 文章封面图未单独存储，需要从正文中提取首图或使用占位
- “分享”数据未持久化，需复用现有指标或返回默认值
- 热搜关键词依赖行为上报数据，若无数据将为空

## 待确认点
- 排行榜默认排序规则（仅按热度/热度+互动权重）
- “分享”字段是否允许用收藏/评论数替代展示
- 路由路径命名（/rank 或 /leaderboard）

## 下一步
生成 CONSENSUS 与 DESIGN 文档，确认组件结构、API 契约与排序规则。
