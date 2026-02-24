# Architecture & Component Plan

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │   Login  │  │  Dashboard   │  │  Sidebar    │  │  API    │  │
│  │  Page    │  │    Page      │  │  Component  │  │  Client │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘  └────┬────┘  │
│       │               │                  │              │        │
│       └───────────────┴──────────────────┴──────────────┘        │
│                              │                                   │
│                     HTTP + JWT Bearer                            │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                        Backend (Django)                         │
│                              │                                   │
│  ┌────────────┐  ┌──────────┴──────────┐  ┌─────────────────┐  │
│  │   CORS     │  │      URLs & Views    │  │    Serializers  │  │
│  │ Middleware │  │   (REST API Endpoints)│  │                 │  │
│  └────────────┘  └──────────┬──────────┘  └─────────────────┘  │
│                              │                                   │
│  ┌────────────┐  ┌──────────┴──────────┐  ┌─────────────────┐  │
│  │   Models   │  │   Authentication     │  │    Cache        │  │
│  │   (DB)     │  │   (JWT + User)       │  │   (Redis)       │  │
│  └────────────┘  └─────────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Celery (Async Tasks)                   │  │
│  │  - update_realtime_metrics (every 5s)                     │  │
│  │  - generate_daily_summary (daily)                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Backend Components

### 1. accounts - 用户认证模块

| Component | File | Function |
|-----------|------|----------|
| **User Model** | `accounts/models.py` | 自定义用户模型，使用 email 作为登录字段 (USERNAME_FIELD='email') |
| **UserSerializer** | `accounts/serializers.py` | 用户数据序列化，包含 id, username, email, first_name, last_name |
| **RegisterSerializer** | `accounts/serializers.py` | 注册序列化器，处理密码写入和用户创建 |
| **RegisterView** | `accounts/views.py` | 用户注册 API (POST /api/register/) |
| **UserDetailView** | `accounts/views.py` | 获取当前用户详情 API (GET /api/user/) |

**API Endpoints:**
- `POST /api/register/` - 用户注册
- `POST /api/login/` - JWT 登录 (由 SimpleJWT 提供)
- `GET /api/user/` - 获取当前用户信息

---

### 2. analytics - 数据分析模块

| Component | File | Function |
|-----------|------|----------|
| **DashboardConfig Model** | `analytics/models.py` | 用户仪表盘配置存储: theme, refresh_interval, widgets |
| **AnalyticsSummary Model** | `analytics/models.py` | 周期性汇总数据: period_type(hourly/daily/weekly), metric_name, value |
| **RealtimeEvent Model** | `analytics/models.py` | 实时事件日志: event_type, data, processed 状态 |
| **RealtimeCache** | `analytics/cache.py` | 实时指标缓存工具 (TTL=10s) |
| **RealtimeDataView** | `analytics/views.py` | 获取实时指标 API (active_users, cpu_usage, memory_usage, rps) |
| **DailySummaryView** | `analytics/views.py` | 获取每日汇总 API (缓存1小时) |
| **ConfigView** | `analytics/views.py` | 获取/更新用户配置 API |
| **update_realtime_metrics** | `analytics/tasks.py` | Celery 任务: 每5秒更新模拟指标数据 |
| **generate_daily_summary** | `analytics/tasks.py` | Celery 任务: 每日生成汇总数据 |

**API Endpoints:**
- `GET /api/analytics/realtime/` - 获取实时指标
- `GET /api/analytics/daily/` - 获取每日汇总
- `GET /api/analytics/config/` - 获取用户配置
- `POST /api/analytics/config/` - 更新用户配置

---

### 3. myproject - Django 项目配置

| Component | File | Function |
|-----------|------|----------|
| **Settings** | `myproject/settings.py` | Django 配置: INSTALLED_APPS, JWT, CORS, Redis, Database |
| **URLs** | `myproject/urls.py` | 主路由配置 |
| **Celery** | `myproject/celery.py` | Celery 应用配置 |

---

## Frontend Components

### 1. Pages

| Page | File | Function |
|------|------|----------|
| **LoginPage** | `js/nextjs-auth/src/app/login/page.tsx` | 用户登录页面: 表单验证、JWT token 存储、错误提示 |
| **DashboardPage** | `js/nextjs-auth/src/app/Dashboard/page.tsx` | 仪表盘首页: 实时指标卡片、每日汇总、用户信息展示 |

### 2. Components

| Component | File | Function |
|-----------|------|----------|
| **Sidebar** | `js/nextjs-auth/src/components/Sidebar.tsx` | 侧边栏导航: 用户信息展示、菜单项、登出功能 |

### 3. Libraries

| Library | File | Function |
|---------|------|----------|
| **API Client** | `js/nextjs-auth/src/lib/api.ts` | Axios 实例: 自动注入 JWT token、封装所有 API 调用函数 |

---

## Data Flow

### 登录流程
```
LoginPage → login() → POST /api/login/ → JWT (access/refresh)
         → localStorage.setItem('access_token')
         → router.push('/Dashboard')
```

### Dashboard 数据流程
```
1. Initial Load:
   DashboardPage → Promise.all([
     getUserProfile()      → GET /api/user/
     getDashboardConfig()  → GET /api/analytics/config/
     getDailySummary()     → GET /api/analytics/daily/
   ])

2. Realtime Polling (every 5s):
   getRealtimeData() → GET /api/analytics/realtime/ → Update UI
```

### 后台任务流程
```
Celery Worker:
  ├─ update_realtime_metrics (every 5s)
  │   └─ RealtimeCache.set_metric() → Redis
  │
  └─ generate_daily_summary (daily)
      └─ AnalyticsSummary.objects.update_or_create() → SQLite
```

---

## 技术栈清单

| Layer | Technology | Version |
|-------|------------|---------|
| Backend Framework | Django | 4.2 |
| API Framework | Django REST Framework | - |
| Authentication | SimpleJWT | - |
| Task Queue | Celery | - |
| Cache | Redis + django-redis | - |
| Frontend Framework | Next.js (App Router) | - |
| UI Framework | Tailwind CSS | - |
| HTTP Client | Axios | - |
| Database | SQLite | - |

---

## 后续开发建议

### Phase 1: 核心功能完善
- [ ] 添加真实数据源替代模拟数据
- [ ] 实现 Charts/图表组件
- [ ] 添加 Settings 页面

### Phase 2: 性能优化
- [ ] 添加 WebSocket 实时推送 (替代轮询)
- [ ] 实现数据分页
- [ ] 添加 CDN 静态资源

### Phase 3: 扩展功能
- [ ] 多用户/团队功能
- [ ] 数据导出 (CSV/Excel)
- [ ] 通知系统
