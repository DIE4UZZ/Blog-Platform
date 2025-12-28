# DESIGN_backend

## 架构概览
```mermaid
flowchart TB
  subgraph API
    U[User Router]
    A[Article Router]
    I[Interaction Router]
    B[Behavior Router]
    R[Recommend Router]
    D[Analysis Router]
  end
  subgraph Service
    US[User Service]
    AS[Article Service]
    IS[Interaction Service]
    BS[Behavior Service]
    RS[Recommend Service]
    DS[Analysis Service]
    Auth[Auth/JWT]
  end
  subgraph Data
    DB[(MySQL)]
  end

  U --> US --> DB
  A --> AS --> DB
  I --> IS --> DB
  B --> BS --> DB
  R --> RS --> DB
  D --> DS --> DB
  U --> Auth
  A --> Auth
  I --> Auth
  B --> Auth
  R --> Auth
  D --> Auth
```

## 分层设计
- Router: 处理参数校验、权限依赖、返回格式
- Service: 业务逻辑与数据库事务
- Model: ORM 模型与数据库结构
- Schema: 请求/响应模型
- Core: 配置、JWT、安全工具

## 模块依赖关系
```mermaid
graph LR
  Router --> Service
  Service --> Model
  Service --> Core
  Router --> Schema
  Core --> Model
```

## 接口契约
- 请求/响应遵循 API.md
- 统一返回结构：{ code, message, data }
- JWT 鉴权：Authorization: Bearer <token>

## 数据流向
```mermaid
sequenceDiagram
  participant FE as Frontend
  participant API as FastAPI
  participant DB as MySQL
  FE->>API: 请求 /api/user/login
  API->>DB: 校验用户
  DB-->>API: 用户记录
  API-->>FE: 返回 token
```

## 异常处理策略
- 统一异常响应格式
- 业务异常返回 4xxx，系统异常返回 5000
- 日志记录错误与关键业务事件
