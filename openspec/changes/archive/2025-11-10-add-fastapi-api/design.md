# 技术设计文档

## 背景 (Context)

当前 Pipeline 是命令行工具,缺乏服务化能力。需要提供 RESTful API 接口,支持:
- 远程调用
- 多用户并发
- 异步处理
- 标准化响应

## 目标与非目标 (Goals / Non-Goals)

### 目标 ✅
1. 提供标准的 RESTful API 接口
2. 支持文件上传与双版本输出
3. 异步处理大文件,避免超时
4. 完整的错误处理与日志
5. 易于部署与扩展

### 非目标 ❌
1. 不实现用户认证/授权 (MVP 阶段)
2. 不提供 WebSocket 实时推送
3. 不实现分布式任务队列 (Celery/RQ)
4. 不存储用户数据 (无状态服务)

## 技术决策 (Decisions)

### 决策 1: 选择 FastAPI 而非 Flask

**理由**:
- ✅ 原生异步支持 (async/await)
- ✅ 自动生成 OpenAPI 文档
- ✅ Pydantic 集成,类型安全
- ✅ 高性能 (基于 Starlette + Uvicorn)
- ✅ 与现有 Pydantic models 无缝集成

**替代方案**: Flask + Flask-RESTX
- ❌ 异步支持较弱
- ❌ 需要额外插件实现文档生成

### 决策 2: 使用 BackgroundTasks 而非 Celery

**理由**:
- ✅ 简单轻量,无需额外依赖 (Redis/RabbitMQ)
- ✅ 适合中小规模并发 (< 100 并发)
- ✅ 快速实现,易于调试

**替代方案**: Celery + Redis
- ❌ 增加部署复杂度
- ❌ MVP 阶段过度设计
- 📝 未来可升级为 Celery (当并发需求 > 100)

### 决策 3: 同步返回 vs 异步任务

**方案**: 混合模式
- 小文件 (< 10MB, < 50 页) → 同步返回
- 大文件 (> 10MB 或 > 50 页) → 异步任务,返回 task_id

**理由**:
- ✅ 兼顾响应速度与稳定性
- ✅ 避免小文件增加轮询开销
- ✅ 大文件不阻塞 API 请求

### 决策 4: 文件存储策略

**方案**: 本地文件系统 + TTL 清理
- 上传文件保存至 `uploads/{task_id}/input.json`
- 输出文件保存至 `outputs/{task_id}/result_*.json`
- 24 小时后自动清理

**替代方案**: 对象存储 (S3/OSS)
- ❌ MVP 阶段不需要
- 📝 未来扩展点 (支持配置切换)

### 决策 5: 响应格式

**标准响应结构**:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "metadata": {
    "task_id": "uuid",
    "timestamp": "2025-11-10T12:00:00Z",
    "processing_time": 3.14
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "上传的文件不是有效的 JSON 格式",
    "details": { ... }
  },
  "metadata": { ... }
}
```

## 架构设计 (Architecture)

### 请求处理流程

```
客户端
  ↓
[POST /api/v1/extract]
  ↓
1. 文件验证 (格式, 大小)
  ↓
2. 保存到 uploads/
  ↓
3. 判断同步/异步
  ↓
├─ 小文件 → 直接处理 → 返回结果
└─ 大文件 → BackgroundTask → 返回 task_id
             ↓
         [Pipeline 处理]
             ↓
         保存到 outputs/
             ↓
         更新任务状态
```

### 目录结构

```
document_tool/
├── api.py                    # FastAPI 主应用
├── api_models.py             # API 数据模型
├── pipline.py                # 核心 Pipeline (不变)
├── uploads/                  # 上传文件临时目录
│   └── {task_id}/
│       └── input.json
├── outputs/                  # 输出结果目录
│   └── {task_id}/
│       ├── result_raw.json
│       └── result_aligned.json
├── .env                      # 环境变量
├── requirements.txt          # 依赖清单
├── Dockerfile                # Docker 镜像
└── docker-compose.yml        # 容器编排
```

### 数据流

```
JSON 文档上传
    ↓
DocumentLoader.load_from_json()
    ↓
ChunkGrouper.group_by_dynamic_size()
    ↓
EntityExtractor.extract_from_chunks() [并行]
    ↓
EntityDeduplicator.deduplicate_entities()
    ↓
OntologyAligner.align_entities()
    ↓
KnowledgeGraphBuilder.build()
    ↓
保存双版本输出
    ↓
返回结果或 task_id
```

## 风险与权衡 (Risks / Trade-offs)

### 风险 1: 内存占用
- **问题**: 大文件并发处理可能导致内存溢出
- **缓解**: 
  - 限制最大并发数 (max_workers 配置)
  - 限制最大文件大小 (50MB)
  - 添加内存监控与告警

### 风险 2: LLM API 调用失败
- **问题**: 外部 API 不稳定,导致处理失败
- **缓解**:
  - Pipeline 已有重试机制 (max_retries=2)
  - 返回详细错误信息
  - 建议用户重试

### 风险 3: 文件存储无限增长
- **问题**: 未清理的文件占满磁盘
- **缓解**:
  - 实现 TTL 清理任务 (24 小时)
  - 添加磁盘空间监控
  - 可配置为对象存储 (未来)

### 权衡 1: 简单 vs 功能完整
- **选择**: 简单优先,快速 MVP
- **放弃**: 认证、分布式队列、WebSocket
- **理由**: 快速验证需求,避免过度设计

### 权衡 2: 性能 vs 资源消耗
- **选择**: 合理并发 (max_workers=3)
- **放弃**: 极致性能 (无限并发)
- **理由**: 避免资源耗尽,稳定优先

## 迁移计划 (Migration Plan)

### 阶段 1: 开发与测试 (Week 1)
- 实现核心 API 端点
- 单元测试 + 集成测试
- 本地验证

### 阶段 2: 部署与文档 (Week 2)
- Docker 镜像构建
- 部署文档编写
- API 使用示例

### 阶段 3: 试运行 (Week 3)
- 小范围用户测试
- 性能监控与优化
- Bug 修复

### 回滚方案
- API 是新增功能,不影响命令行接口
- 如需回滚,直接停止 API 服务即可
- 原有 `pipline.py` 命令行功能不受影响

## 开放问题 (Open Questions)

1. **Q**: 是否需要实现速率限制?
   - **A**: MVP 阶段不实现,后续根据滥用情况决定

2. **Q**: 是否需要支持批量上传?
   - **A**: 暂不支持,用户可多次调用 API

3. **Q**: 是否需要持久化任务状态?
   - **A**: MVP 使用内存存储,重启丢失,可接受
   - 未来可升级为 Redis 或数据库

4. **Q**: 输出格式是直接返回 JSON 还是文件下载?
   - **A**: 两种方式都支持
     - 小结果 (< 5MB): 直接返回 JSON
     - 大结果 (> 5MB): 返回下载链接

## 未来扩展 (Future Enhancements)

### Phase 2 (3-6 个月)
- 用户认证与 API Key 管理
- 分布式任务队列 (Celery)
- 对象存储集成 (S3/OSS)
- WebSocket 实时进度推送

### Phase 3 (6-12 个月)
- 多租户支持
- 任务优先级队列
- 自动扩缩容 (Kubernetes)
- 监控告警系统 (Prometheus + Grafana)
