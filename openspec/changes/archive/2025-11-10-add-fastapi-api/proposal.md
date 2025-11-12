# 变更提案: 添加 FastAPI RESTful API 接口

## 为什么 (Why)

当前 Pipeline 只能通过命令行使用,缺乏程序化调用方式。需要提供 RESTful API 接口,支持:
- 远程调用知识图谱提取服务
- 文件上传与异步处理
- 标准化的 API 响应格式
- 服务化部署能力

这是将 Pipeline 从单机工具演进为企业级服务的关键一步。

## 做什么 (What Changes)

### 新增功能
- ✅ 创建 FastAPI 应用服务 (`api.py`)
- ✅ 实现文件上传接口 (`POST /api/v1/extract`)
- ✅ 支持上传解析后的 JSON 文档
- ✅ 返回双版本知识图谱 (raw + aligned)
- ✅ 添加健康检查接口 (`GET /api/v1/health`)
- ✅ 添加任务状态查询接口 (`GET /api/v1/tasks/{task_id}`)
- ✅ 支持异步处理大文件
- ✅ 配置化参数支持 (chunk_size, max_workers 等)

### 技术栈
- FastAPI (异步 Web 框架)
- Pydantic (请求/响应验证)
- Uvicorn (ASGI 服务器)
- python-multipart (文件上传)

### **非破坏性变更**
- 不修改现有 `pipline.py` 核心逻辑
- 保持命令行接口完全兼容
- API 作为新的访问层,封装 Pipeline

## 影响范围 (Impact)

### 受影响的规范
- **新增**: `specs/api/spec.md` (API 接口规范)
- **引用**: `specs/pipeline/spec.md` (Pipeline 作为底层服务)

### 受影响的代码
- **新增**: `api.py` (FastAPI 应用)
- **新增**: `api_models.py` (API 数据模型)
- **新增**: `.env.example` (环境变量示例)
- **更新**: `README_PIPELINE.md` (添加 API 使用说明)

### 新增依赖
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
aiofiles>=23.0.0
```

### 部署影响
- 需要开放 HTTP 端口 (默认 8000)
- 需要配置文件上传目录权限
- 建议使用 Docker 容器化部署
