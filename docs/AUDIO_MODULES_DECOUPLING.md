# 音频模块解耦说明

## 变更概述

音频功能已解耦为独立的短音频和长音频模块，支持独立部署和迁移。

## 新目录结构

```
api/
└── audio/                          # 音频模块总目录
    ├── __init__.py                 # 导出短/长音频路由
    ├── shared_models.py            # 共享数据模型
    ├── short/                      # 短音频模块（独立）
    │   ├── __init__.py
    │   ├── models.py               # 短音频数据模型
    │   └── routes.py               # 短音频API路由
    └── long/                       # 长音频模块（独立）
        ├── __init__.py
        ├── models.py               # 长音频数据模型
        └── routes.py               # 长音频API路由
```

## 模块依赖关系

### 短音频模块 (`api/audio/short/`)
**依赖的Pipeline**:
- `pipelines/audio_pipeline.py` - 短音频转写和纪要生成

**功能**:
- `/api/v1/audio/transcribe` - 上传音频文件，立即转写
- `/api/v1/audio/download/{task_id}` - 下载会议纪要
- `/api/v1/audio/health` - 健康检查

**独立性**: ✅ 完全独立，无长音频依赖

---

### 长音频模块 (`api/audio/long/`)
**依赖的Pipeline**:
- `pipelines/paraformer_long_audio.py` - DashScope paraformer异步服务
- `pipelines/meeting_minutes_service.py` - 会议纪要生成（共享）
- `pipelines/storage.py` - OSS存储客户端
- `db/database.py` - PostgreSQL数据库

**功能**:
- `/api/v1/audio/transcribe-long` - 提交长音频URL任务
- `/api/v1/audio/transcribe-long/{task_id}` - 查询任务状态
- `/api/v1/audio/dashscope/tasks` - 代理DashScope任务列表
- `/api/v1/audio/dashscope/tasks/{id}` - 代理DashScope任务详情
- `/api/v1/audio/dashscope/tasks/{id}/cancel` - 取消任务
- `/api/v1/audio/health` - 健康检查

**独立性**: ✅ 完全独立，无短音频依赖

---

### 共享模块 (`api/audio/shared_models.py`)
**共享的数据模型**:
- `AudioMetadata` - 音频元数据
- `MeetingMinutes` - 会议纪要结构
- `ProcessingStats` - 处理统计信息

## 迁移指南

### 场景1: 只迁移短音频模块

**需要复制的文件**:
```
api/audio/
├── __init__.py (仅导入 short_audio_router)
├── shared_models.py
└── short/
    ├── __init__.py
    ├── models.py
    └── routes.py

pipelines/
├── audio_pipeline.py
└── prompts/
    └── meeting_minutes.txt
```

**main.py 修改**:
```python
# 只导入短音频路由
from api.audio.short import router as short_audio_router
app.include_router(short_audio_router)
```

---

### 场景2: 只迁移长音频模块

**需要复制的文件**:
```
api/audio/
├── __init__.py (仅导入 long_audio_router)
├── shared_models.py
└── long/
    ├── __init__.py
    ├── models.py
    └── routes.py

pipelines/
├── paraformer_long_audio.py
├── meeting_minutes_service.py
├── storage.py
└── prompts/
    └── meeting_minutes.txt

db/
└── database.py
```

**环境变量需求**:
```bash
# DashScope
DASHSCOPE_API_KEY=xxx

# 长音频存储
LONG_AUDIO_STORAGE_DIR=uploads/audios/long
LONG_AUDIO_RESULT_TTL=86400
LONG_AUDIO_POLL_INTERVAL=10

# OSS（可选）
OSS_ENDPOINT=https://oss-xxx.aliyuncs.com
OSS_BUCKET=your-bucket
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx

# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db
```

**main.py 修改**:
```python
# 只导入长音频路由
from api.audio.long import router as long_audio_router
app.include_router(long_audio_router)
```

---

### 场景3: 同时部署短+长音频（当前默认）

**main.py 配置**:
```python
from api.audio import short_audio_router, long_audio_router
app.include_router(short_audio_router)
app.include_router(long_audio_router)
```

## 向后兼容性

### API端点保持不变
所有原有的API端点路径和参数保持完全一致：

**短音频**:
- ✅ `POST /api/v1/audio/transcribe`
- ✅ `GET /api/v1/audio/download/{task_id}`

**长音频**:
- ✅ `POST /api/v1/audio/transcribe-long`
- ✅ `GET /api/v1/audio/transcribe-long/{task_id}`
- ✅ `GET /api/v1/audio/dashscope/tasks`
- ✅ `GET /api/v1/audio/dashscope/tasks/{id}`
- ✅ `POST /api/v1/audio/dashscope/tasks/{id}/cancel`

### 数据模型保持不变
所有Pydantic模型的字段、类型、验证规则完全一致，无breaking changes。

## 优势

1. **独立部署**: 可以只部署短音频或长音频服务
2. **清晰边界**: 模块职责明确，互不干扰
3. **易于维护**: 每个模块的代码更聚焦，便于理解和修改
4. **灵活扩展**: 可以独立升级某一模块
5. **减少耦合**: 短音频不依赖OSS/数据库，轻量级部署

## 旧文件处理

原有的 `api/audio_api.py` 和 `api/audio_models.py` 可以保留作为参考，或在验证新模块功能正常后删除。

建议：
- 先运行测试确保新模块功能正常
- 再考虑删除旧文件

## 测试验证

### 测试短音频
```bash
curl -X POST http://localhost:8000/api/v1/audio/transcribe \
  -F "file=@test.m4a" \
  -F "output_format=json"
```

### 测试长音频
```bash
curl -X POST http://localhost:8000/api/v1/audio/transcribe-long \
  -H "Content-Type: application/json" \
  -d '{
    "file_urls": ["https://example.com/audio.mp3"],
    "model": "paraformer-v2"
  }'
```

### 健康检查
```bash
# 短音频健康检查（会返回不同的 service 标识）
curl http://localhost:8000/api/v1/audio/health

# 长音频会有不同的health端点返回
```

## 注意事项

1. **健康检查端点**: 两个模块都有 `/api/v1/audio/health`，FastAPI会注册最后一个，建议区分路径或合并逻辑
2. **环境变量**: 长音频需要更多环境变量配置（OSS、数据库）
3. **数据库迁移**: 长音频模块会自动创建 `long_audio_tasks` 表
4. **日志标识**: 可以通过日志中的 `[short-audio]` 或 `[long-audio]` tag区分

## 更新日期

2025-11-18
