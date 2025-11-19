# Huey 任务队列设置指南

## 概述

本项目使用 **Huey** 作为分布式任务队列框架，用于异步处理 PDF 提取任务。Huey 基于 Redis 存储，支持多 worker 部署和自动重试机制。

## 架构

```
┌──────────────────┐
│   FastAPI 应用   │
│  (API 服务器)    │
└────────┬─────────┘
         │ 提交任务
         ↓
┌──────────────────┐
│   Redis 队列     │
│ (任务持久化)     │
└────────┬─────────┘
         │ 消费任务
         ↓
┌──────────────────┐
│  Huey Workers    │
│ (后台处理进程)   │
└──────────────────┘
```

## 安装依赖

```bash
pip install redis>=4.5.0 huey>=2.4.5
```

## 配置

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# Redis 连接
HUEY_REDIS_URL=redis://:password@localhost:6379

# 队列名称
HUEY_QUEUE_NAME=pdf-tasks

# Worker 配置
HUEY_WORKERS=5                    # Worker 进程数
HUEY_WORKER_TYPE=thread           # thread 或 process

# 开发环境：同步执行（不使用队列）
HUEY_IMMEDIATE=false
```

### Redis 连接示例

**本地开发（WSL）**：
```bash
HUEY_REDIS_URL=redis://:200105@localhost:6379
```

**生产环境**：
```bash
HUEY_REDIS_URL=redis://:your_password@redis.example.com:6379
```

## 启动方式

### 方式 1: 使用启动脚本

**Linux/WSL**：
```bash
bash scripts/start_huey_worker.sh
```

**Windows**：
```cmd
scripts\start_huey_worker.bat
```

### 方式 2: 直接命令行

```bash
# 5 个线程 worker
huey_consumer pipelines.tasks.huey -w 5 -k thread -v

# 5 个进程 worker（多核利用）
huey_consumer pipelines.tasks.huey -w 5 -k process -v

# 单个 worker（开发环境）
huey_consumer pipelines.tasks.huey -w 1 -k thread -v
```

### 方式 3: 开发环境同步执行

设置环境变量后，任务会同步执行（无需启动 worker）：

```bash
export HUEY_IMMEDIATE=true
python -m uvicorn api.main:app --reload
```

## 任务定义

### 创建任务

在 `pipelines/tasks.py` 中定义任务：

```python
from pipelines.tasks import huey

@huey.task(retries=3, retry_delay=60)
def pdf_extract_process_task(task_id: str):
    """处理 PDF 提取任务"""
    service = PDFExtractionService()
    service.process_pdf(task_id)
```

### 提交任务

在 API 路由中提交任务：

```python
from pipelines.tasks import pdf_extract_process_task

# 立即提交
pdf_extract_process_task(task_id)

# 延迟提交（5 分钟后）
pdf_extract_process_task.schedule((task_id,), delay=300)
```

## 重试机制

Huey 内置重试支持：

```python
@huey.task(retries=3, retry_delay=60)
def my_task():
    """失败时最多重试 3 次，每次间隔 60 秒"""
    pass
```

**重试流程**：
1. 任务执行失败，抛出异常
2. Huey 记录错误并将任务重新入队
3. 等待 `retry_delay` 秒后重新执行
4. 重复直到成功或达到 `retries` 次数

## 监控

### 查看队列状态

```bash
# 连接 Redis CLI
redis-cli -a password

# 查看队列长度
LLEN pdf-tasks

# 查看队列内容
LRANGE pdf-tasks 0 -1

# 查看结果存储
KEYS huey:*
```

### API 端点

```bash
# 获取队列状态
curl http://localhost:8000/api/v1/pdf/queue/status

# 健康检查
curl http://localhost:8000/api/v1/pdf/health
```

## 故障排查

### 问题 1: Redis 连接失败

```
ConnectionError: Error 111 connecting to localhost:6379
```

**解决**：
1. 检查 Redis 是否运行：`redis-cli ping`
2. 检查连接 URL 和密码
3. 检查防火墙规则

### 问题 2: Worker 进程不消费任务

```
# 检查 worker 是否运行
ps aux | grep huey_consumer

# 查看 worker 日志
huey_consumer pipelines.tasks.huey -w 5 -k thread -v
```

### 问题 3: 任务一直重试

**原因**：
- 任务代码有 bug
- 外部依赖不可用（API、数据库等）

**解决**：
1. 查看 worker 日志
2. 检查任务代码
3. 检查外部依赖

### 问题 4: 内存占用过高

**原因**：
- Worker 数量过多
- 任务处理时间过长

**解决**：
- 减少 worker 数量：`-w 3`
- 优化任务代码
- 增加服务器资源

## 生产部署

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 启动 Huey worker
CMD ["huey_consumer", "pipelines.tasks.huey", "-w", "5", "-k", "thread", "-v"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass password

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      HUEY_REDIS_URL: redis://:password@redis:6379
    command: uvicorn api.main:app --host 0.0.0.0

  worker:
    build: .
    environment:
      HUEY_REDIS_URL: redis://:password@redis:6379
      HUEY_WORKERS: 5
    command: huey_consumer pipelines.tasks.huey -w 5 -k thread -v
    depends_on:
      - redis
```

### 进程管理（Supervisor）

```ini
[program:huey-worker]
command=huey_consumer pipelines.tasks.huey -w 5 -k thread -v
directory=/path/to/project
autostart=true
autorestart=true
stderr_logfile=/var/log/huey-worker.err.log
stdout_logfile=/var/log/huey-worker.out.log
```

## 最佳实践

1. **使用线程 worker**（`-k thread`）用于 I/O 密集型任务
2. **使用进程 worker**（`-k process`）用于 CPU 密集型任务
3. **设置合理的重试次数**（通常 3 次）
4. **监控队列长度**和 worker 状态
5. **定期清理 Redis**中的过期数据
6. **使用日志聚合**（ELK、Datadog 等）

## 参考资源

- [Huey 官方文档](https://huey.readthedocs.io/)
- [Redis 官方文档](https://redis.io/documentation)
- [项目设计文档](../openspec/changes/add-pdf-pipeline/design.md)

---

**最后更新**: 2025-11-19  
**版本**: 1.0
