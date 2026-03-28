# CONSENSUS_leaderboard

## 需求共识
1. 新增“排行榜”页面，展示榜单列表、热搜词、推荐关注三块区域。
2. 榜单列表包含：排名、标题、摘要、封面图（可为空）、热度值、分享值、发布时间。
3. 热搜区支持“换一换”刷新；推荐关注列表支持“关注”交互（前端状态模拟即可）。
4. 数据来源由后端 API 提供；前端遵循现有请求封装与组件风格。
5. 实现顺序：先完成前端页面与交互，再补齐后端接口。

## 验收标准
- 路由可访问排行榜页面，页面布局与截图风格一致。
- 榜单列表加载、分页、空状态与加载状态正常。
- 热搜与推荐关注可加载，热搜支持刷新。
- 后端接口返回字段与前端期望一致，前后端联调可正常渲染。

## 接口与字段约定（初稿）
- GET `/api/rank/list`
  - 参数：page、page_size、category、keyword
  - 返回：list、total、page、page_size
  - list item：article_id、title、summary、cover、hot_value、share_count、create_time
- GET `/api/rank/hot-search`
  - 参数：page、page_size
  - 返回：list、total、page、page_size
  - list item：keyword、count、is_hot
- GET `/api/rank/recommend`
  - 参数：limit
  - 返回：list
  - list item：user_id、name、desc、article_count、view_count、followed

## 未决问题
- 统一“分享”字段定义与计算策略。
- 封面图提取规则与缺省占位图是否需要后端提供。
