┌──────────────────────────────────────────────────────────────────────────┐
│                         传感器设备层 (IoT Devices)                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐ │
│  │  Raspberry Pi #1    │  │  Raspberry Pi #2    │  │  Raspberry Pi #N │ │
│  │ (Room 101)          │  │ (Room 102)          │  │ (Room N)         │ │
│  │ mmWave Radar Sensor │  │ mmWave Radar Sensor │  │ mmWave Sensor    │ │
│  │ - Heart Rate (HR)   │  │ - Heart Rate (HR)   │  │ - Heart Rate     │ │
│  │ - Respiration (RR)  │  │ - Respiration (RR)  │  │ - Respiration    │ │
│  │ - Activity Status   │  │ - Activity Status   │  │ - Activity       │ │
│  │ - In Bed            │  │ - In Bed            │  │ - In Bed         │ │
│  │ - In Room           │  │ - In Room           │  │ - In Room        │ │
│  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬─────────┘ │
└─────────────┼──────────────────────┼───────────────────────┼────────────┘
              │                      │                       │
              │ MQTT Publish         │                       │
              │ esp/room/<id>/vitals │                       │
              │                      │                       │
┌─────────────┴──────────────────────┴───────────────────────┴────────────┐
│                         MQTT Broker (Mosquitto)                         │
│                    (Running on Raspberry Pi or VM)                      │
│  mqtt://localhost:1883                                                  │
│  Topics:                                                                │
│    - esp/room/101/vitals    (Heart, Respiration, Activity, etc.)       │
│    - esp/room/102/vitals                                               │
│    - esp/room/N/vitals                                                 │
│    - alerts/room/101        (Fall detected, Room departure, etc.)       │
│    - control/room/101       (Commands to device)                        │
└─────────────┬──────────────────────────────────────────────────────────┘
              │
              │ MQTT Subscribe
              │
┌─────────────▼──────────────────────────────────────────────────────────┐
│                     Backend (Django + Celery)                           │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ MQTT Bridge Service (Celery Task / Standalone Service)            ││
│  │  - MQTT Client: paho-mqtt (Subscribe to esp/room/*/vitals)        ││
│  │  - On receive:                                                     ││
│  │    1. Parse vital data (HR, RR, Activity, In Bed, In Room)        ││
│  │    2. Save to ResidentVitals DB (with timestamp)                  ││
│  │    3. Publish to Redis Pub/Sub: vitals:room:<id>                  ││
│  │    4. Check alert conditions (fall, room departure)               ││
│  │    5. Publish alerts to Redis: alerts:room:<id>                   ││
│  └────────────────────────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ Django REST API                                                    ││
│  │  - GET /api/residents/                (List residents)             ││
│  │  - GET /api/residents/<id>/           (Resident detail)            ││
│  │  - POST /api/residents/<id>/dismiss/  (Dismiss alert)              ││
│  │  - GET /api/residents/<id>/history/   (Historical data)            ││
│  │  - WebSocket: /ws/residents/<id>/     (Real-time vitals)           ││
│  └────────────────────────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ Redis (Cache + Pub/Sub)                                            ││
│  │  - Channel: vitals:room:<id>   (Latest vitals for each room)       ││
│  │  - Channel: alerts:room:<id>   (Current alerts)                    ││
│  │  - Cache: resident:<id>        (Resident config cache)             ││
│  └────────────────────────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ Database (PostgreSQL/SQLite)                                       ││
│  │  - ResidentVitals (streaming data with timestamps)                 ││
│  │  - ResidentEvent (alert events)                                    ││
│  │  - Resident (config)                                               ││
│  └────────────────────────────────────────────────────────────────────┘│
└─────────────┬──────────────────────────────────────────────────────────┘
              │
              │ WebSocket + REST
              │
┌─────────────▼──────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                                   │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ WebSocket Client (per resident detail page)                       ││
│  │  - Connect: ws://localhost:8000/ws/residents/<id>/                ││
│  │  - On message: Update real-time vitals + chart                    ││
│  │  - Automatic reconnect on disconnect                              ││
│  └────────────────────────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ Dashboard (30s polling fallback for list view)                     ││
│  │  - GET /api/residents/ (polls every 30s if WebSocket unavailable) ││
│  │  - Shows real-time alerts via WebSocket or polling                ││
│  └────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘



Raspberry Pi → MQTT → Django → Redis → Frontend
Time: T0
┌─────────────────────────┐
│  Raspberry Pi #1        │
│  mmWave Radar Sensor    │
└────────────┬────────────┘
             │ Read vital signs every 1-2 seconds
             │ Package: {
             │   "resident_id": "101",
             │   "heart_rate": 72,
             │   "respiration": 18,
             │   "activity_status": "sitting",
             │   "in_bed": false,
             │   "in_room": true,
             │   "timestamp": "2024-02-10T14:30:45Z"
             │ }
             │
             ▼
┌──────────────────────────────┐
│  MQTT Broker                 │
│  Topic: esp/room/101/vitals  │
│  QoS: 1 (At least once)      │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Django MQTT Bridge          │
│  (Celery Task or Service)    │
│  - Subscribe to all topics   │
│  - Parse JSON payload        │
└────────────┬─────────────────┘
             │
        ┌────┴─────────────────────┐
        │                          │
        ▼                          ▼
┌──────────────────────┐  ┌─────────────────────┐
│  Save to Database    │  │  Publish to Redis   │
│  ResidentVitals()    │  │  PubSub Channel:    │
│  - Create record     │  │  vitals:room:101    │
│  - Timestamp: now()  │  │                     │
│  - All vitals        │  │  Message: {         │
│  - Mark: synced=true │  │    vitals object    │
│                      │  │  }                  │
└──────────┬───────────┘  └────────┬────────────┘
           │                       │
           │                       ▼
           │              ┌──────────────────────┐
           │              │  WebSocket Server    │
           │              │  Channel: room:101   │
           │              │  - Broadcast vitals  │
           │              │  - To all connected  │
           │              │    clients           │
           │              └────────┬─────────────┘
           │                       │
           │                       ▼
           │              ┌──────────────────────┐
           │              │  Frontend            │
           │              │  ResidentDetailPage  │
           │              │  - Real-time update  │
           │              │  - Chart.js re-draw  │
           │              │  - Vitals card       │
           │              └──────────────────────┘
           │
           ▼
    ┌──────────────────┐
    │  Alert Check     │
    │  - Is HR > 120?  │
    │  - Not in bed +  │
    │    lying_down?   │
    │  - Out of room   │
    │    at night?     │
    └────────┬─────────┘
             │
        ┌────┴──────────────┐
        │                   │
        ▼                   ▼
     [Alert]            [No Alert]
        │                   │
        ▼                   │
   Publish to:              │
   Redis Channel:           │
   alerts:room:101          │
   Message: {               │
     "event": "fall",       │
     "timestamp": now       │
   }                        │
        │                   │
        ▼                   │
   Create ResidentEvent()   │
   event_type: "fall"       │
        │                   │
        └───────┬───────────┘
                │
                ▼
         Frontend receives
         alert notification
         via WebSocket




"""
场景：Resident 101 的心率从 72 变成 85
对比 REST 轮询 vs WebSocket 推送
"""

# ============================================================================
# 方案 1️⃣: REST API 轮询（原架构）
# ============================================================================

print("=" * 80)
print("方案 1️⃣: REST API 轮询 - Frontend 每30秒拉取一次")
print("=" * 80)

# ────────────────────────────────────────────────────────────────────────────
# BACKEND: Django REST API
# ────────────────────────────────────────────────────────────────────────────

"""
# django/analytics/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Resident, ResidentVitals

class ResidentListView(APIView):
    '''REST API 端点'''
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        '''
        前端轮询调用这个接口
        GET /api/residents/
        '''
        print("[T0] Frontend 发送 GET /api/residents/")
        
        # 查询所有 active 的 residents
        residents = Resident.objects.filter(is_active=True)
        
        # 为每个 resident 获取最新的 vitals
        data = []
        for resident in residents:
            # 查询最新一条 vitals 数据
            latest_vitals = ResidentVitals.objects.filter(
                resident=resident
            ).latest('recorded_at')
            
            print(f"[T10ms] Django 查询 DB: Resident {resident.room_number}")
            
            data.append({
                'id': resident.id,
                'name': resident.name,
                'room_number': resident.room_number,
                'latest_vitals': {
                    'heart_rate': latest_vitals.heart_rate,  # 85
                    'respiration': latest_vitals.respiration,
                    'activity_status': latest_vitals.activity_status,
                    'in_bed': latest_vitals.in_bed,
                    'in_room': latest_vitals.in_room,
                    'recorded_at': latest_vitals.recorded_at.isoformat(),
                }
            })
        
        print(f"[T20ms] Django 返回 JSON 响应")
        return Response(data)


class ResidentDetailView(APIView):
    '''REST API 详情端点'''
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resident_id):
        '''
        前端点击"View Details"后调用
        GET /api/residents/101/
        '''
        print(f"[T30ms] Frontend 发送 GET /api/residents/{resident_id}/")
        
        resident = Resident.objects.get(id=resident_id)
        latest_vitals = ResidentVitals.objects.filter(
            resident=resident
        ).latest('recorded_at')
        
        print(f"[T40ms] Django 查询数据库并返回")
        
        return Response({
            'id': resident.id,
            'name': resident.name,
            'room_number': resident.room_number,
            'latest_vitals': {
                'heart_rate': latest_vitals.heart_rate,
                'respiration': latest_vitals.respiration,
                'activity_status': latest_vitals.activity_status,
                'in_bed': latest_vitals.in_bed,
                'in_room': latest_vitals.in_room,
                'recorded_at': latest_vitals.recorded_at.isoformat(),
            }
        })
"""

# ────────────────────────────────────────────────────────────────────────────
# FRONTEND: React/Next.js 轮询
# ────────────────────────────────────────────────────────────────────────────

"""
// src/app/Residents/page.tsx
// ResidentsPage - 列表页面

'use client';

import { useEffect, useState } from 'react';
import { getResidents } from '@/src/lib/api';

export default function ResidentsPage() {
  const [residents, setResidents] = useState([]);

  useEffect(() => {
    // ✅ 初始化 - 立即获取一次
    console.log("[T0] Frontend: 页面加载，立即获取数据");
    const fetchInitial = async () => {
      const data = await getResidents();
      // data = [{
      //   id: 1,
      //   name: "John Doe",
      //   room_number: "101",
      //   latest_vitals: { heart_rate: 72, ... }
      // }]
      setResidents(data);
      console.log("[T50ms] Frontend: 收到数据并显示");
    };
    fetchInitial();

    // ✅ 定时轮询 - 每30秒拉取一次
    const interval = setInterval(async () => {
      console.log("[T30s] Frontend: 定时轮询，发送 GET /api/residents/");
      
      const data = await getResidents();
      setResidents(data);
      console.log("[T30s+50ms] Frontend: 收到数据，更新 UI");
    }, 30000);  // ⚠️ 每30秒轮询一次

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {residents.map((resident) => (
        <div key={resident.id} className="bg-white rounded-lg shadow p-4">
          <h3>{resident.name}</h3>
          <p>Room: {resident.room_number}</p>
          <div className="mt-4">
            <span>❤️ {resident.latest_vitals.heart_rate} bpm</span>
            {/* 显示最后更新时间 */}
            <p className="text-xs text-gray-500">
              Updated: {new Date(resident.latest_vitals.recorded_at).toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
"""

# ────────────────────────────────────────────────────────────────────────────
# 时间线：用户在列表页看到数据更新
# ────────────────────────────────────────────────────────────────────────────

print("\n📊 时间线：Heart Rate 72 → 85 的过程")
print("-" * 80)

timeline_rest = """
T0秒:          Frontend 加载页面
               ├─ useEffect 触发
               └─ 调用 getResidents()
               
T0+50ms:       ✓ Frontend 收到响应并显示
               ├─ Heart Rate: 72 bpm
               └─ 页面显示数据

T0+2秒:        📱 Raspberry Pi 读取传感器
               └─ Heart Rate 变成 85 bpm
               
T0+3秒:        💾 Django 数据库已更新
               └─ ResidentVitals.objects.create(heart_rate=85)
               
T0+15秒:       ⏳ Frontend 仍在显示旧数据
               ├─ Heart Rate: 72 bpm（过时！）
               └─ 用户看不到新值

T0+30秒:       Frontend 定时轮询触发
               └─ 发送 GET /api/residents/
               
T0+30+50ms:    ✓ Frontend 收到新数据
               ├─ Heart Rate: 85 bpm（终于更新！）
               └─ 页面重新渲染
               
T0+60秒:       Frontend 第二次轮询
T0+90秒:       Frontend 第三次轮询
... 依此类推，每30秒轮询一次 ...
"""
print(timeline_rest)

print("\n⚠️ 问题分析：")
print("- 延迟: 最多 30 秒才能看到新数据")
print("- 浪费: 无数据更新时仍在轮询")
print("- 流量: 200 个用户 × 30 秒轮询 = 每分钟 400 个请求！")
print("- 准确: 不实时，用户看到过时数据")


# ============================================================================
# 方案 2️⃣: WebSocket 推送（新架构）
# ============================================================================

print("\n" + "=" * 80)
print("方案 2️⃣: WebSocket 推送 - Django 主动推送实时数据")
print("=" * 80)

# ────────────────────────────────────────────────────────────────────────────
# BACKEND: MQTT Bridge - 接收传感器数据
# ────────────────────────────────────────────────────────────────────────────

"""
# django/analytics/mqtt_bridge.py

import paho.mqtt.client as mqtt
import json
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class MQTTBridge:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.channel_layer = get_channel_layer()
    
    def on_message(self, client, userdata, msg):
        '''
        MQTT 消息到达时立即触发
        Topic: esp/room/101/vitals
        Payload: {
            "resident_id": "101",
            "heart_rate": 85,
            "respiration": 18,
            "activity_status": "sitting",
            "in_bed": false,
            "in_room": true,
            "timestamp": "2024-02-10T14:30:45Z"
        }
        '''
        print("[T+2s] MQTT Bridge: 收到消息")
        
        payload = json.loads(msg.payload.decode())
        resident_id = payload['resident_id']
        
        print(f"[T+2s+5ms] Django: 处理 Resident {resident_id}")
        
        # 第1步: 保存到数据库
        from .models import Resident, ResidentVitals
        
        resident = Resident.objects.get(room_number=resident_id)
        vitals = ResidentVitals.objects.create(
            resident=resident,
            heart_rate=payload['heart_rate'],  # 85
            respiration=payload['respiration'],
            activity_status=payload['activity_status'],
            in_bed=payload['in_bed'],
            in_room=payload['in_room'],
        )
        
        print(f"[T+2s+10ms] Django: 保存到数据库")
        
        # 第2步: 保存到 Redis 缓存
        cache.set(f'vitals:room:{resident_id}', {
            'heart_rate': vitals.heart_rate,
            'respiration': vitals.respiration,
            'activity_status': vitals.activity_status,
            'in_bed': vitals.in_bed,
            'in_room': vitals.in_room,
            'recorded_at': vitals.recorded_at.isoformat(),
        }, timeout=300)
        
        print(f"[T+2s+11ms] Django: 缓存到 Redis")
        
        # 第3步: 广播到 WebSocket
        self.broadcast_vitals_to_websocket(resident_id, vitals)
    
    def broadcast_vitals_to_websocket(self, resident_id, vitals):
        '''广播给所有连接的 WebSocket 客户端'''
        print(f"[T+2s+12ms] Django: 广播到 WebSocket group")
        
        async_to_sync(self.channel_layer.group_send)(
            f'vitals_room_{resident_id}',  # Group name
            {
                'type': 'vitals_update',  # 对应 Consumer 的方法
                'data': {
                    'heart_rate': vitals.heart_rate,
                    'respiration': vitals.respiration,
                    'activity_status': vitals.activity_status,
                    'in_bed': vitals.in_bed,
                    'in_room': vitals.in_room,
                    'recorded_at': vitals.recorded_at.isoformat(),
                }
            }
        )
"""

# ────────────────────────────────────────────────────────────────────────────
# BACKEND: Django Channels Consumer - WebSocket 处理
# ────────────────────────────────────────────────────────────────────────────

"""
# django/analytics/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class VitalsConsumer(AsyncWebsocketConsumer):
    '''
    WebSocket Consumer
    客户端连接: ws://localhost:8000/ws/residents/101/
    '''
    
    async def connect(self):
        '''客户端连接时'''
        self.resident_id = self.scope['url_route']['kwargs']['resident_id']
        self.group_name = f'vitals_room_{self.resident_id}'
        
        print(f"[T0] WebSocket: 客户端连接到 /ws/residents/{self.resident_id}/")
        
        # 加入 group，这样可以接收 group_send 的消息
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        print(f"[T0+5ms] WebSocket: 加入 group '{self.group_name}'")
        
        # 接受连接
        await self.accept()
        
        print(f"[T0+10ms] WebSocket: 连接建立完成")
    
    async def vitals_update(self, event):
        '''
        当 MQTT Bridge 发送 group_send 时，这个方法被调用
        
        event = {
            'type': 'vitals_update',
            'data': {
                'heart_rate': 85,
                'respiration': 18,
                ...
            }
        }
        '''
        print(f"[T+2s+15ms] Consumer: 收到 vitals_update 事件")
        
        # 发送给客户端
        await self.send(text_data=json.dumps({
            'type': 'vitals_update',
            'data': event['data']
        }))
        
        print(f"[T+2s+16ms] Consumer: 发送给客户端")
"""

# ────────────────────────────────────────────────────────────────────────────
# FRONTEND: WebSocket 客户端 - 实时接收数据
# ────────────────────────────────────────────────────────────────────────────

"""
// src/app/Residents/[id]/page.tsx
// ResidentDetailPage - 详情页面

'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

export default function ResidentDetailPage() {
  const params = useParams();
  const residentId = params.id;
  
  const [vitals, setVitals] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    console.log("[T0] Frontend: 建立 WebSocket 连接");
    
    // 创建 WebSocket 连接（持久化）
    const ws = new WebSocket(
      `ws://localhost:8000/ws/residents/${residentId}/`
    );
    
    ws.onopen = () => {
      console.log("[T0+50ms] Frontend: WebSocket 已连接");
      setWsConnected(true);
    };
    
    ws.onmessage = (event) => {
      '''
      实时接收来自 Django 的推送消息
      message = {
        type: 'vitals_update',
        data: {
          heart_rate: 85,
          respiration: 18,
          ...
        }
      }
      '''
      console.log("[T+2s+50ms] Frontend: 收到 WebSocket 消息");
      
      const message = JSON.parse(event.data);
      
      if (message.type === 'vitals_update') {
        console.log(`[T+2s+51ms] Frontend: 更新数据 - Heart Rate: ${message.data.heart_rate}`);
        
        // 立即更新状态
        setVitals(message.data);
        
        // 更新 Chart.js 图表
        updateChart(message.data);
        
        // 更新卡片显示
        // Component re-render 自动发生
      }
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
    
    ws.onclose = () => {
      console.log("WebSocket closed");
      setWsConnected(false);
    };
    
    return () => {
      ws.close();
    };
  }, [residentId]);

  return (
    <div>
      {/* 连接状态指示 */}
      <div className={wsConnected ? 'text-green-600' : 'text-red-600'}>
        {wsConnected ? '🟢 Real-time Connected' : '🔴 Disconnected'}
      </div>
      
      {/* 体征数据 - 实时更新 */}
      {vitals && (
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-gray-500">Heart Rate</p>
            <p className="text-3xl font-bold">
              {vitals.heart_rate}  {/* 实时更新，无需刷新 */}
            </p>
            <p className="text-xs text-gray-400">bpm</p>
          </div>
          
          <div>
            <p className="text-gray-500">Respiration</p>
            <p className="text-3xl font-bold">{vitals.respiration}</p>
            <p className="text-xs text-gray-400">/min</p>
          </div>
          
          <div>
            <p className="text-gray-500">Last Update</p>
            <p className="text-sm">
              {new Date(vitals.recorded_at).toLocaleTimeString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
"""

# ────────────────────────────────────────────────────────────────────────────
# 时间线：用户在详情页看到实时数据更新
# ────────────────────────────────────────────────────────────────────────────

print("\n📊 时间线：Heart Rate 72 → 85 的过程")
print("-" * 80)

timeline_ws = """
T0秒:          Frontend 打开详情页面
               ├─ useEffect 触发
               └─ 建立 WebSocket 连接
               
T0+50ms:       ✓ WebSocket 连接建立
               └─ 准备接收实时数据

T0+2秒:        📱 Raspberry Pi 读取传感器
               └─ Heart Rate 变成 85 bpm
               
T0+2+10ms:     MQTT Publish
               └─ esp/room/101/vitals → {heart_rate: 85}
               
T0+2+20ms:     ✓ Django MQTT Bridge 接收
               ├─ 保存到数据库
               ├─ 缓存到 Redis
               └─ 广播到 WebSocket group
               
T0+2+30ms:     ✓ Django Channels Consumer 发送
               └─ WebSocket 消息推送
               
T0+2+50ms:     ✓ Frontend 接收 WebSocket 消息
               ├─ setVitals({heart_rate: 85, ...})
               ├─ updateChart(...)
               └─ 页面自动更新
               
T0+2+60ms:     ✓ 用户看到新值
               └─ Heart Rate: 85 bpm（实时！）

后续:          每次传感器更新 → 立即推送 → 立即显示
               延迟 < 100ms，连续更新
"""
print(timeline_ws)

print("\n✅ 优点分析：")
print("- 延迟: 50ms（几乎实时！）")
print("- 高效: 只推送有变化的数据")
print("- 流量: 200 个用户，每 2 秒 1 条消息 = 每分钟 6000 条（共享连接）")
print("- 准确: 始终看到最新数据")


# ============================================================================
# 比较总结
# ============================================================================

print("\n" + "=" * 80)
print("完整对比")
print("=" * 80)

comparison = """
┌──────────────────┬────────────────────────┬────────────────────────┐
│      方面        │      REST 轮询         │      WebSocket 推送     │
├──────────────────┼────────────────────────┼────────────────────────┤
│ 延迟             │ 30秒 ❌                 │ 50ms ✅                 │
│ 网络请求数       │ 每30秒 1次 ❌           │ 连续推送（共享）✅      │
│ 数据库查询       │ 频繁 ❌                 │ 仅首次 ✅               │
│ 服务器负载       │ 高 ❌                  │ 低 ✅                   │
│ 用户体验         │ 看到过时数据 ❌         │ 实时更新 ✅             │
│ 复杂度           │ 简单 ✅                 │ 中等 ~                 │
│ 扩展性（100用户） │ 每分钟200请求          │ 共享 WebSocket 连接    │
└──────────────────┴────────────────────────┴────────────────────────┘

性能数字对比：
- 延迟改进: 30秒 → 50ms = 600 倍快
- 数据库查询: 200次/分钟 → 0次/分钟 = 无穷倍减少
- 网络流量: 200个用户 × 30秒 = 400请求/分钟 vs 6000条消息/分钟共享
- 内存使用: 轮询会占用更多数据库连接，推送占用 WebSocket 连接
"""
print(comparison)