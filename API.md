下面先给你一份**接口设计文档草稿**，是基于我们刚整理的需求来的，重点考虑“前端要怎么调”。  
你可以直接拿它去对照前端页面开发，如果后面后端实现时有调整，我们再一起迭代。

---

## 一、接口设计总说明

### 1.1 基本约定

- **Base URL**：`/api`
- **数据格式**：  
  - 请求：`application/json`（GET 参数仍使用 query string）  
  - 响应：`application/json`
- **统一返回格式**：

```json
{
  "code": 0,
  "message": "ok",
  "data": { }
}
```

- **错误码约定（示例）**：
  - `0`：成功  
  - `4001`：参数错误  
  - `4002`：未登录或 Token 失效  
  - `4003`：权限不足  
  - `5000`：服务器内部错误  

### 1.2 鉴权约定

- 登录后返回 `token`，前端在后续请求中通过请求头携带：
  - `Authorization: Bearer <token>`

---

## 二、用户相关接口

### 2.1 用户注册

- **URL**：`POST /api/user/register`  
- **是否需要登录**：否  
- **请求体（JSON）**：

```json
{
  "username": "testuser",
  "password": "123456",
  "email": "test@example.com",
  "phone": "13800000000"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "user_id": 1
  }
}
```

---

### 2.2 用户登录

- **URL**：`POST /api/user/login`  
- **是否需要登录**：否  
- **请求体（JSON）**（用户名或邮箱其一即可）：

```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "123456"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "user_id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "token": "jwt-token-string"
  }
}
```

---

### 2.3 获取当前登录用户信息

- **URL**：`GET /api/user/info`  
- **是否需要登录**：是  
- **请求头**：`Authorization: Bearer <token>`  
- **请求参数**：无  
- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone": "13800000000",
    "preference_tags": "AI,Python,推荐系统",
    "create_time": "2025-03-01 10:00:00",
    "last_login_time": "2025-03-10 09:00:00"
  }
}
```

---

### 2.4 更新用户偏好标签

- **URL**：`PUT /api/user/preference`  
- **是否需要登录**：是  
- **请求体（JSON）**：

```json
{
  "preference_tags": "AI,Python,推荐系统"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "更新成功",
  "data": {}
}
```

> 前端使用场景：个人中心页面的“兴趣标签”设置。

---

## 三、文章相关接口

### 3.1 发布文章

- **URL**：`POST /api/article/publish`  
- **是否需要登录**：是（博主/注册用户）  
- **请求体（JSON）**：

```json
{
  "title": "我的第一篇博客",
  "content": "# Markdown 原文内容",
  "category": "技术",
  "tags": "Python,AI,推荐系统",
  "status": "published"   // 可选: "draft" / "published"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "发布成功",
  "data": {
    "article_id": 1001
  }
}
```

> 前端使用场景：文章发布页面“提交/发布”按钮。

---

### 3.2 编辑文章

- **URL**：`PUT /api/article/edit`  
- **是否需要登录**：是（仅作者可编辑）  
- **请求体（JSON）**：

```json
{
  "article_id": 1001,
  "title": "更新后的标题",
  "content": "# 更新后的 Markdown 内容",
  "category": "技术",
  "tags": "Python,AI",
  "status": "published"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "编辑成功",
  "data": {}
}
```

---

### 3.3 删除文章（可选）

- **URL**：`DELETE /api/article/delete`  
- **是否需要登录**：是（仅作者或管理员）  
- **请求参数（Query）**：

```text
article_id=1001
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "删除成功",
  "data": {}
}
```

> 若你前端暂时不做“删除”功能，可以先不实现。

---

### 3.4 获取文章详情

- **URL**：`GET /api/article/detail`  
- **是否需要登录**：否  
- **请求参数（Query）**：

```text
article_id=1001
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "article_id": 1001,
    "title": "我的第一篇博客",
    "content": "# Markdown 原文内容",
    "html_content": "<h1>渲染后的 HTML</h1>",
    "category": "技术",
    "tags": ["Python", "AI", "推荐系统"],
    "author": {
      "user_id": 1,
      "username": "testuser"
    },
    "view_count": 123,
    "like_count": 10,
    "collect_count": 5,
    "create_time": "2025-03-01 10:00:00",
    "update_time": "2025-03-02 11:00:00",
    "is_liked": false,      // 登录用户视角，仅登录时有
    "is_collected": true    // 登录用户视角，仅登录时有
  }
}
```

> 前端使用场景：文章详情页渲染。

---

### 3.5 获取文章列表（通用列表）

- **URL**：`GET /api/article/list`  
- **是否需要登录**：否  
- **请求参数（Query，可选）**：

```text
page=1
page_size=10
category=技术
tags=Python,AI
keyword=推荐系统
order=latest  // latest / hottest 等
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "article_id": 1001,
        "title": "我的第一篇博客",
        "summary": "截取前 N 字作为摘要...",
        "category": "技术",
        "tags": ["Python", "AI"],
        "author": {
          "user_id": 1,
          "username": "testuser"
        },
        "view_count": 123,
        "like_count": 10,
        "collect_count": 5,
        "create_time": "2025-03-01 10:00:00"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

> 前端使用场景：  
> - 分类/标签页列表  
> - 搜索结果页（前端传 `keyword`）

---

### 3.6 获取当前用户的文章列表（个人中心）

- **URL**：`GET /api/article/my-list`  
- **是否需要登录**：是  
- **请求参数（Query）**：

```text
page=1
page_size=10
status=published // 可选: draft/published
```

- **返回示例**：同上 `list` 结构。

> 前端使用场景：个人中心的“我的文章”列表。

---

## 四、互动与行为相关接口

### 4.1 点赞 / 取消点赞

- **URL**：`POST /api/article/like`  
- **是否需要登录**：是  
- **请求体（JSON）**：

```json
{
  "article_id": 1001,
  "action": "like"   // "like" or "unlike"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {
    "like_count": 11,
    "is_liked": true
  }
}
```

> 前端：文章详情页或列表的点赞按钮。

---

### 4.2 收藏 / 取消收藏

- **URL**：`POST /api/article/collect`  
- **是否需要登录**：是  
- **请求体（JSON）**：

```json
{
  "article_id": 1001,
  "action": "collect"   // "collect" or "uncollect"
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {
    "collect_count": 6,
    "is_collected": true
  }
}
```

> 前端：文章详情页或列表的收藏按钮。

---

### 4.3 提交评论

- **URL**：`POST /api/behavior/comment`  
- **是否需要登录**：是  
- **请求体（JSON）**：

```json
{
  "article_id": 1001,
  "content": "这篇文章写得很好！",
  "parent_id": 0  // 0 表示一级评论，非 0 表示回复某条评论
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "评论成功",
  "data": {
    "comment_id": 5001,
    "create_time": "2025-03-02 12:00:00"
  }
}
```

---

### 4.4 获取评论列表

> 原始需求里只定义了“提交评论”，为了前端展示方便，这里加一个**评论列表接口**。

- **URL**：`GET /api/comment/list`  
- **是否需要登录**：否  
- **请求参数（Query）**：

```text
article_id=1001
page=1
page_size=10
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "comment_id": 5001,
        "user": {
          "user_id": 2,
          "username": "commenter"
        },
        "content": "这篇文章写得很好！",
        "parent_id": 0,
        "create_time": "2025-03-02 12:00:00"
      }
    ],
    "total": 20,
    "page": 1,
    "page_size": 10
  }
}
```

---

### 4.5 行为数据上报（阅读/滚动/搜索等）

- **URL**：`POST /api/behavior/report`  
- **是否需要登录**：是（如允许未登录行为，也可以 user_id 为空）  
- **请求体（JSON）**：

```json
{
  "user_id": 1,
  "article_id": 1001,
  "behavior_type": "read",   // read / like / collect / comment / search
  "read_duration": 120,      // 秒，仅 read
  "scroll_depth": 0.85,      // 0-1，仅 read
  "keyword": "推荐系统"       // 仅 search
}
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "上报成功",
  "data": {}
}
```

> 前端：在文章阅读页、搜索结果页，通过埋点/定时/页面卸载事件上报。

---

## 五、推荐相关接口

### 5.1 获取首页推荐文章列表

- **URL**：`GET /api/recommend/list`  
- **是否需要登录**：可选  
  - 未登录：走热门/冷启动策略  
  - 已登录：走个性化推荐  
- **请求参数（Query）**：

```text
page=1
page_size=10
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "article_id": 1001,
        "title": "推荐文章标题",
        "summary": "摘要...",
        "category": "技术",
        "tags": ["Python"],
        "author": {
          "user_id": 1,
          "username": "testuser"
        },
        "view_count": 123,
        "like_count": 10,
        "collect_count": 5,
        "create_time": "2025-03-01 10:00:00",
        "recommend_type": "content_based",   // content_based / collaborative / cold_start
        "recommend_score": 87.5
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

> 前端使用场景：**首页主列表**（可以直接用这个，而不是普通 `article/list`）。

---

### 5.2 获取相似文章推荐（详情页侧栏）

- **URL**：`GET /api/recommend/similar`  
- **是否需要登录**：否（登录时可个性化排序）  
- **请求参数（Query）**：

```text
article_id=1001
size=5
```

- **返回示例**：结构同 `recommend/list` 中 `list` 元素，只是数量较少。

> 前端使用场景：文章详情页“你可能还喜欢 / 相关文章”。

---

## 六、数据分析相关接口（仪表盘）

> 这些接口主要给**博主/管理员后台页面**用，前端前期可以先确定整体结构，后面实现时按需简化。

### 6.1 阅读趋势

- **URL**：`GET /api/analysis/read-trend`  
- **是否需要登录**：是（博主身份）  
- **请求参数（Query）**：

```text
user_id=1
start_date=2025-03-01
end_date=2025-03-31
granularity=day   // day / week / month
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "dates": ["2025-03-01", "2025-03-02"],
    "read_counts": [100, 120],
    "avg_read_duration": [80, 90]
  }
}
```

---

### 6.2 推荐效果

- **URL**：`GET /api/analysis/recommend-effect`  
- **请求参数（Query）**：

```text
user_id=1
start_date=2025-03-01
end_date=2025-03-31
```

- **返回示例**（示意）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "click_through_rate": 0.25,
    "conversion_rate": 0.10,
    "daily": [
      {
        "date": "2025-03-01",
        "ctr": 0.2,
        "conversion": 0.08
      }
    ]
  }
}
```

---

### 6.3 用户画像

- **URL**：`GET /api/analysis/user-portrait`  
- **请求参数（Query）**：

```text
user_id=1
```

- **返回示例**（可根据实际简化或使用模拟数据）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "interest_tags_top10": [
      { "tag": "Python", "weight": 0.4 },
      { "tag": "AI", "weight": 0.3 }
    ],
    "active_hours": [
      { "hour": 20, "count": 50 }
    ]
  }
}
```

---

### 6.4 内容表现

- **URL**：`GET /api/analysis/content-performance`  
- **请求参数（Query）**：

```text
user_id=1
limit=10
```

- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "articles": [
      {
        "article_id": 1001,
        "title": "文章标题",
        "view_count": 123,
        "like_count": 10,
        "collect_count": 5,
        "comment_count": 3,
        "engagement_rate": 0.2
      }
    ]
  }
}
```

---

## 七、接口与前端页面的对应关系（给你一个快速映射）

- **登录/注册页**：  
  - `POST /api/user/register`  
  - `POST /api/user/login`  
  - `GET /api/user/info`（登录后获取用户信息）

- **首页（推荐流）**：  
  - `GET /api/recommend/list`

- **文章列表页（按分类/标签/搜索）**：  
  - `GET /api/article/list`

- **文章详情页**：  
  - `GET /api/article/detail`  
  - `POST /api/article/like`  
  - `POST /api/article/collect`  
  - `GET /api/comment/list`  
  - `POST /api/behavior/comment`  
  - `GET /api/recommend/similar`

- **文章发布/编辑页**：  
  - `POST /api/article/publish`  
  - `PUT /api/article/edit`  
  - （必要时）`GET /api/article/detail` 预填表单

- **个人中心页**：  
  - `GET /api/user/info`  
  - `PUT /api/user/preference`  
  - `GET /api/article/my-list`

- **数据分析仪表盘页**：  
  - `GET /api/analysis/read-trend`  
  - `GET /api/analysis/recommend-effect`  
  - `GET /api/analysis/user-portrait`  
  - `GET /api/analysis/content-performance`

---
