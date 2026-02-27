# 项目启动步骤

## 前置要求
- Python 3.13+
- Node.js 18+
- Redis (用于缓存)

---

## 1. 启动 Django 后端

```bash
# 进入项目目录
cd D:\mmwave_webpage_prototype

# 首次运行需要迁移数据库 (仅第一次)
python manage.py makemigrations
python manage.py migrate

# 启动 Django 服务器
python manage.py runserver 8000
```

访问: http://127.0.0.1:8000

---

## 2. 启动 Next.js 前端

```bash
# 进入前端目录
cd D:\mmwave_webpage_prototype\js\nextjs-auth

# 安装依赖 (仅第一次)
npm install

# 启动开发服务器
npm run dev
```

访问: http://localhost:3000

---

## 3. 启动 Celery Worker (可选 - 生成模拟数据)

```bash
# 进入项目目录
cd D:\mmwave_webpage_prototype

# 启动 worker (处理实时任务)
celery -A myproject worker -l info

# 启动 beat (调度定时任务) - 新开一个 terminal
celery -A myproject beat -l info
```

---

## 登录账号

- Email: `admin@example.com`
- Password: `admin123`

---

## 常用命令

```bash
# 创建测试数据 ( residents )
python manage.py shell -c "from analytics.tasks import create_sample_residents; print(create_sample_residents())"

# 创建管理员用户
python manage.py createsuperuser
```

---

## 目录结构

```
mmwave_webpage_prototype/
├── manage.py                 # Django 入口
├── myproject/               # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── accounts/                # 用户认证模块
│   ├── models.py
│   ├── views.py
│   └── serializers.py
├── analytics/               # 数据分析模块
│   ├── models.py           # Resident, ResidentVitals, ResidentEvent
│   ├── views.py            # API Views
│   ├── serializers.py
│   ├── tasks.py            # Celery 任务
│   └── urls.py
├── js/
│   └── nextjs-auth/        # Next.js 前端
│       ├── src/
│       │   ├── app/
│       │   │   ├── login/
│       │   │   └── Dashboard/
│       │   ├── components/
│       │   └── lib/api.ts
│       └── package.json
└── docs/
    └── ARCHITECTURE_PLAN.md
```
