# CONSENSUS_backend

## 明确需求
- FastAPI + MySQL，实现 API.md 全量接口
- JWT 认证，token 24h 有效
- 用户表字段包含 email、password、role
- 注册/登录仅校验 email + password
- 接口返回格式统一为 code/message/data

## 权限规则
- 未登录：可访问文章列表/详情、推荐列表、评论列表
- 登录用户：可发布/编辑/点赞/收藏/评论/上报行为
- 管理员：拥有更高权限（如删除任意文章、访问全量分析数据）

## 验收标准
- API.md 全量接口可调用，响应结构一致
- 登录后通过 Authorization: Bearer <token> 完成鉴权
- 用户权限控制生效（普通用户无法删除他人文章）
- 数据库模型与接口字段匹配
- 关键逻辑具备基础测试

## 技术与实现约束
- SQLAlchemy 作为 ORM，MySQL 作为存储
- 使用环境变量保存数据库与 JWT 配置
- 代码保持可读性，函数级注释齐全

## 边界限制
- 推荐/分析采用基础统计与简单规则实现
- 不实现 token 刷新与复杂推荐算法
