# 项目启动步骤

## 前置要求

- Python 3.13+
- Node.js 18+
- Docker Desktop（使用 WSL 2 backend，运行项目专用 Redis）
- Mosquitto MQTT Broker (用于接收毫米波传感器数据)

> `requirements.txt` 中的 `paho-mqtt` 只是 MQTT 客户端，不包含 MQTT
> Broker。若只需启动网页或使用模拟数据，可以不启动 Mosquitto；若需接收
> ESP/毫米波传感器的实时数据，则必须单独安装并运行 Mosquitto。

---

## 1. 启动项目专用 Docker Redis

Python `venv` 只能隔离 Python 包，不能在 `venv` 内安装 Docker。为了不影响
本机其他服务使用的 Windows Redis `6379`，本项目使用独立 Docker Container，
并映射到本机 `6380`：

```text
Windows Redis：127.0.0.1:6379（其他本机服务，可继续运行）
Docker Redis： 127.0.0.1:6380（仅本项目使用）
```

不需要执行 `Stop-Service Redis`。首次创建并启动项目 Redis：

```powershell
- start docker destop if on windows

#run this at the first time only to create container

docker run -d --name mmwave-redis --restart unless-stopped -p 127.0.0.1:6380:6379 redis:7.4-alpine 
```

`6380` 是 Windows 主机端口，`6379` 是 Container 内部端口。Container 已经
创建过时，不要再次执行 `docker run`，使用：

```powershell
docker start mmwave-redis
```

检查 Container 和 Redis：

```powershell
docker ps --filter "name=mmwave-redis"
docker exec mmwave-redis redis-cli PING
Test-NetConnection 127.0.0.1 -Port 6380
```

正常结果应包含：

```text
PONG
TcpTestSucceeded : True
```

项目的 [settings.py](../myproject/settings.py) 通过 `REDIS_HOST` 和
`REDIS_PORT` 环境变量配置连接。默认连接项目专用的 `127.0.0.1:6380`，
并按用途使用不同的逻辑 DB：

```python
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))
REDIS_BASE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_BASE_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"{REDIS_BASE_URL}/2"],
        },
    },
}

CELERY_BROKER_URL = f"{REDIS_BASE_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_BASE_URL}/0"
```

如需临时连接其他 Redis，请在启动 Django、Celery 或其他项目进程的每个
PowerShell terminal 中先设置：

```powershell
$env:REDIS_HOST = "127.0.0.1"
$env:REDIS_PORT = "6379"
```

| 功能 | 地址 | Redis DB |
| --- | --- | ---: |
| Celery Broker/Result | `127.0.0.1:6380` | 0 |
| Django Cache | `127.0.0.1:6380` | 1 |
| Channels/WebSocket | `127.0.0.1:6380` | 2 |

---

## 2. 安装并启动 Mosquitto（实时传感器数据）

Windows 用户可从
[Mosquitto 官方下载页面](https://mosquitto.org/download/)下载安装程序。
安装完成后，确认 Mosquitto 服务正在运行：

```powershell
Get-Service mosquitto
Start-Service mosquitto  # 仅在服务尚未运行时执行，可能需要管理员权限
```

如果没有安装为 Windows 服务，也可以在单独的 terminal 中运行：

```powershell
mosquitto -v
```
检查 `1883` 端口：

```powershell
netstat -ano | Select-String ":1883"
```

正常结果应包含：

```text
TCP  127.0.0.1:1883  0.0.0.0:0  LISTENING
```

测试 MQTT Publish/Subscribe。在第一个 PowerShell terminal 中订阅：

```powershell
& "C:\Program Files\mosquitto\mosquitto_sub.exe" `
  -h 127.0.0.1 -p 1883 -t "test/#" -v
```

在第二个 PowerShell terminal 中发布：

```powershell
& "C:\Program Files\mosquitto\mosquitto_pub.exe" `
  -h 127.0.0.1 -p 1883 -t "test/check" -m "hello"
```

第一个 terminal 应显示：

```text
test/check hello
```

项目默认连接本机 Broker：

| 配置 | 默认值 |
| --- | --- |
| Broker 地址 | `127.0.0.1` |
| Broker 端口 | `1883` |
| 订阅主题 | `esp/room/+/vitals` |

如 Broker 位于其他设备，可在启动 MQTT 订阅程序前设置环境变量：

```powershell
$env:MQTT_BROKER_HOST = "192.168.1.100"
$env:MQTT_BROKER_PORT = "1883"
```

---

## 3. 启动 Django 后端

```powershell
# 进入项目目录
cd D:\mmwave_webpage_prototype

# 首次运行需要迁移数据库 (仅第一次)
.\venv\Scripts\python.exe manage.py makemigrations
.\venv\Scripts\python.exe manage.py migrate

# 启动 Django 服务器
.\venv\Scripts\python.exe manage.py runserver 8000
```

访问: http://127.0.0.1:8000

---

## 4. 启动 MQTT 订阅程序（实时传感器数据）

Mosquitto 和 Django 启动后，打开另一个 terminal：

```powershell
cd D:\mmwave_webpage_prototype
.\venv\Scripts\python.exe manage.py runmqtt
```

连接成功后应显示：

```text
Connecting to MQTT broker 127.0.0.1:1883
Subscribed to esp/room/+/vitals
```

此进程负责从 Mosquitto 接收传感器消息、保存生命体征数据，并将更新推送给
前端。它需要在实时数据采集期间持续运行。

---

## 5. 启动 Next.js 前端

```powershell
# 进入前端目录
cd D:\mmwave_webpage_prototype\js\nextjs-auth

# 安装依赖 (仅第一次)
npm install

# 启动开发服务器
npm run dev
```

访问: http://localhost:3000

---

## 6. 启动 Celery Worker（必需）

Celery Worker 负责处理 alarm dismiss 后的延迟检查。用户 dismiss alarm 后，
Django 会将 `check_alert_after_dismiss` 任务延迟 5 分钟发送到 Redis 队列。
如果 Worker 没有运行，这项检查不会执行，alarm 也不会按预期自动恢复。

请先确认 Redis 已启动，然后在单独的 terminal 中启动 Worker：

```powershell
# 进入项目目录
cd D:\mmwave_webpage_prototype

# 必需：处理 alarm dismiss 等后台任务
.\venv\Scripts\celery.exe -A myproject worker -l info
```

Celery Beat 不负责 alarm dismiss 检查。它只负责按小时生成模拟 resident
events，因此是可选服务。需要模拟事件时，在另一个 terminal 中启动：

```powershell
cd D:\mmwave_webpage_prototype
.\venv\Scripts\celery.exe -A myproject beat -l info
```

---

## 登录账号

- Email: `admin@example.com`
- Password: `admin123`

---

## 常用命令

```powershell
# 创建测试数据 ( residents )
.\venv\Scripts\python.exe manage.py shell -c "from analytics.tasks import create_sample_residents; print(create_sample_residents())"

# 创建管理员用户
.\venv\Scripts\python.exe manage.py createsuperuser
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
