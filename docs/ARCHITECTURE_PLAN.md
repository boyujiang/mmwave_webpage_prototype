# Architecture & Component Plan

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js / App Router)              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │   Login  │  │  Dashboard   │  │  Residents   │  │  API    │  │
│  │  Page    │  │    Page      │  │  Pages       │  │  Client │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬───────┘  └────┬────┘  │
│       │               │                  │              │        │
│       └───────────────┴──────────────────┴──────────────┘        │
│                              │                                   │
│                     HTTP + JWT Bearer                            │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                       Backend (Django)                          │
│                              │                                   │
│  ┌────────────┐  ┌──────────┴──────────┐  ┌─────────────────┐  │
│  │   CORS     │  │      URLs & Views    │  │   Serializers   │  │
│  │ Middleware │  │   (REST API Endpoints)│  │                 │  │
│  └────────────┘  └──────────┬──────────┘  └─────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────┴──────────────────────────┐        │
│  │                    Models (DB)                       │        │
│  │  Resident, ResidentVitals, ResidentEvent, AlertNote │        │
│  │  DashboardConfig, AnalyticsSummary, RealtimeEvent   │        │
│  └──────────────────────────┬──────────────────────────┘        │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  Celery (Async Tasks)                      │  │
│  │  - update_resident_vitals (every 30s)                     │  │
│  │  - generate_resident_events (hourly, overnight bias)      │  │
│  │  - generate_historical_data (bulk backfill)               │  │
│  │  - check_alert_after_dismiss (5min delay check)           │  │
│  │  - check_and_restore_alert (5min delay restore)           │  │
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

#### Models

| Model | File | Fields / Purpose |
|-------|------|-----------------|
| **DashboardConfig** | `analytics/models.py` | 用户仪表盘配置: theme, refresh_interval, widgets |
| **AnalyticsSummary** | `analytics/models.py` | 周期汇总数据: period_type, period_start, metric_name, value (hourly/daily/weekly) |
| **RealtimeEvent** | `analytics/models.py` | 实时事件日志: event_type, data, processed |
| **Resident** | `analytics/models.py` | 居民静态信息: name, room_number (unique), date_of_birth, is_active, alert_dismissed_at |
| **ResidentVitals** | `analytics/models.py` | 居民体征数据: heart_rate, respiration, activity_status, in_bed, in_room, recorded_at (FK → Resident) |
| **ResidentEvent** | `analytics/models.py` | 居民事件: event_type (bathroom_run/fall_detected/medication_taken/exited_room/returned_room), timestamp, metadata |
| **AlertNote** | `analytics/models.py` | 护理人员警报笔记: alert_type, note, caregiver_name, is_dismissed, dismissed_at (FK → Resident) |

#### Serializers

| Serializer | File | Purpose |
|-----------|------|---------|
| **ResidentVitalsSerializer** | `analytics/serializers.py` | 序列化 heart_rate, respiration, activity_status, in_bed, in_room, recorded_at |
| **ResidentEventSerializer** | `analytics/serializers.py` | 序列化 event_type + display, timestamp, metadata |
| **ResidentSerializer** | `analytics/serializers.py` | 完整居民详情: 含 latest_vitals, today_bathroom_runs, latest_events, status (computed) |
| **ResidentListSerializer** | `analytics/serializers.py` | 列表用精简序列化: id, name, room_number, status |
| **AlertNoteSerializer** | `analytics/serializers.py` | 序列化 alert_type, note, caregiver_name, created_at, is_dismissed |

**status 计算逻辑** (在 Serializer 中):
- `fall_detected`: not in_bed + activity_status == lying_down
- `room_departure`: not in_bed + not in_room + 夜间 (22-6点)
- `stable`: 默认

#### Views

| View | File | Function |
|------|------|----------|
| **ConfigView** | `analytics/views.py` | 获取/更新用户仪表盘配置 |
| **ResidentListView** | `analytics/views.py` | 获取所有 active 居民列表 (含 vitals, events) |
| **ResidentDetailView** | `analytics/views.py` | 获取单个居民完整详情 |
| **ResidentVitalsHistoryView** | `analytics/views.py` | 获取体征历史数据 (chart 用), 支持 metric=hr/rr/activity/br/f + range=hour/day/week |
| **AlertNoteView** | `analytics/views.py` | 基于文件的护理笔记 CRUD (JSON 文件存储于 analytics/notes/<resident_id>/) |
| **DismissAlertView** | `analytics/views.py` | 解除警报: 设置 alert_dismissed_at, 调度 5min 后检查任务 |
| **ToggleResidentActiveView** | `analytics/views.py` | 切换 resident 的 is_active 状态 |

**API Endpoints:**
- `GET /api/analytics/config/` - 获取用户配置
- `POST /api/analytics/config/` - 更新用户配置
- `GET /api/analytics/residents/` - 获取所有 residents
- `GET /api/analytics/residents/<id>/` - 获取单个 resident 详情
- `GET /api/analytics/residents/<id>/history/?metric=hr&range=day` - 获取体征历史 (chart data)
- `GET /api/analytics/residents/<id>/notes/` - 获取 caregiver 笔记
- `POST /api/analytics/residents/<id>/notes/` - 创建 caregiver 笔记
- `POST /api/analytics/residents/<id>/dismiss/` - 解除警报
- `POST /api/analytics/residents/<id>/toggle-active/` - 切换激活状态

#### Celery Tasks

| Task | File | Frequency | Description |
|-----|------|-----------|-------------|
| **update_resident_vitals** | `analytics/tasks.py` | Every 30s | 更新所有 residents 的心率/呼吸/活动/床位状态 |
| **generate_resident_events** | `analytics/tasks.py` | Hourly | 生成 bathroom runs (夜间优先, 最多5次/晚) + room 出入事件 |
| **create_sample_residents** | `analytics/tasks.py` | One-shot | 创建 4 个测试 resident |
| **generate_historical_data** | `analytics/tasks.py` | One-shot | 批量生成数周的模拟历史数据 (30min 间隔, 含 fall 事件) |
| **check_alert_after_dismiss** | `analytics/tasks.py` | On-demand | 解除警报 5min 后检查是否仍需显示警报 |
| **check_and_restore_alert** | `analytics/tasks.py` | On-demand | 5min 后自动恢复警报 (用于测试) |

---

### 3. myproject - Django 项目配置

| Component | File | Function |
|-----------|------|----------|
| **Settings** | `myproject/settings.py` | Django 配置: INSTALLED_APPS, JWT, CORS, Database (SQLite) |
| **URLs** | `myproject/urls.py` | 主路由配置 |
| **Celery** | `myproject/celery.py` | Celery 应用配置 |

---

## Frontend Components

### 1. Pages

| Page | File | Function |
|------|------|----------|
| **LoginPage** | `js/nextjs-auth/src/app/login/page.tsx` | 用户登录页面: 表单验证、JWT token 存储、错误提示 |
| **DashboardPage** | `js/nextjs-auth/src/app/Dashboard/page.tsx` | 仪表盘首页: 实时警报列表 + 概览统计 + 居民列表 (30s 轮询) |
| **ResidentsPage** | `js/nextjs-auth/src/app/Residents/page.tsx` | 居民列表页: 卡片网格布局, 搜索过滤, 状态/体征/事件展示 |
| **ResidentDetailPage** | `js/nextjs-auth/src/app/Residents/[id]/page.tsx` | 居民详情页: Chart.js 体征趋势图, 7 种指标切换, range 切换, caregiver 笔记, 解除警报 |

### 2. Components

| Component | File | Function |
|-----------|------|----------|
| **Sidebar** | `js/nextjs-auth/src/components/Sidebar.tsx` | 侧边栏导航: 用户信息展示、Dashboard/Residents 菜单项、登出功能 |

### 3. Libraries

| Library | File | Function |
|---------|------|----------|
| **API Client** | `js/nextjs-auth/src/lib/api.ts` | Axios 实例: 自动注入 JWT token, 封装所有 API 调用 (login, register, user, residents, history, notes, dismiss, toggle) |

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
     getUserProfile()    → GET /api/user/
     getResidents()      → GET /api/analytics/residents/
   ])

2. Polling (every 30s):
   getResidents() → GET /api/analytics/residents/ → Update alerts + cards
```

### Resident Detail 数据流程
```
1. Initial Load:
   ResidentDetailPage → Promise.all([
     getUserProfile()              → GET /api/user/
     getResidents()                → GET /api/analytics/residents/
     getAlertNotes(residentId)     → GET /api/analytics/residents/<id>/notes/
   ])

2. Metric Switch:
   getResidentVitalsHistory(id, metric, range) → GET /api/analytics/residents/<id>/history/?metric=hr&range=day
   → Chart.js Line re-render

3. Dismiss Alert:
   dismissAlert(id) → POST /api/analytics/residents/<id>/dismiss/
   → Backend schedules check_alert_after_dismiss (5min)

4. Create Note:
   createAlertNote(id, note, alert_type) → POST /api/analytics/residents/<id>/notes/
   → Saved to analytics/notes/<id>/<timestamp>.json
```

### 后台任务流程 (Celery Beat)
```
Celery Worker:
  ├─ update_resident_vitals (every 30s)
  │   └─ ResidentVitals.objects.create() for each active resident
  │
  └─ generate_resident_events (hourly)
      └─ ResidentEvent.objects.create() (bathroom runs, exited/returned room)
```

---

## 技术栈清单

| Layer | Technology | Version |
|-------|------------|---------|
| Backend Framework | Django | 4.2 |
| API Framework | Django REST Framework | 3.x |
| Authentication | SimpleJWT | - |
| Task Queue | Celery + celery-beat | - |
| Cache | Redis + django-redis | - |
| Frontend Framework | Next.js (App Router) | - |
| UI Framework | Tailwind CSS | - |
| Charts | Chart.js + react-chartjs-2 | - |
| HTTP Client | Axios | - |
| Database | SQLite | - |

---

## 后续开发建议

### Phase 1: 核心功能完善
- [ ] 添加真实 mmWave 雷达数据源替代模拟数据
- [ ] 添加 Settings 页面 (用户配置)
- [ ] 添加多语言/国际化支持

### Phase 2: 性能优化
- [ ] 添加 WebSocket 实时推送 (替代 30s 轮询)
- [ ] 实现数据分页 (居民列表)
- [ ] 迁移 PostgreSQL (生产环境)

### Phase 3: 扩展功能
- [ ] 多用户/团队功能 (不同用户管理不同居民)
- [ ] 数据导出 (CSV/PDF 报告)
- [ ] 通知系统 (Email/SMS 警报)
- [ ] 居民健康趋势 AI 分析
