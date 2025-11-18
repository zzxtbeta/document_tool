# API 规范: PDF 商业计划书智能解析

## 概述

本文档定义 PDF 商业计划书智能解析功能的 API 行为规范,使用 BDD (Behavior-Driven Development) 格式描述。

## API 端点

### 1. 提交 PDF 解析任务

**端点**: `POST /api/v1/pdf/extract`

#### Scenario 1.1: 成功提交单个 PDF 解析任务

**Given**: 用户已准备好一个有效的 PDF 文件  
**When**: 用户使用 multipart/form-data 上传 PDF 文件  
**Then**: 
- 响应状态码应为 `202 Accepted`
- 响应体应包含 `task_id` (UUID 格式)
- 响应体应包含 `task_status` 字段,值为 `PENDING`
- 响应体应包含 `model` 字段,值为 `qwen3-vl-flash`
- 响应体应包含 `pdf_url` 字段,指向 OSS 上的原始 PDF
- PDF 文件应被上传到 OSS 路径: `bronze/userUploads/{projectId}/pdf/{taskId}/original.pdf`
- 数据库应创建一条新记录,状态为 `PENDING`
- 任务应被提交到异步队列

**请求示例**:
```http
POST /api/v1/pdf/extract
Content-Type: multipart/form-data

file=@startup_bp_2025.pdf
user_id=user123
project_id=project456
source_filename=startup_bp_2025.pdf
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_status": "PENDING",
    "model": "qwen3-vl-flash",
    "pdf_url": "https://oss-cn-hangzhou.aliyuncs.com/.../original.pdf",
    "page_count": 15,
    "submitted_at": "2025-11-18T10:30:00Z",
    "queue_position": 3
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z",
    "estimated_time": "30-60s"
  }
}
```

#### Scenario 1.1b: 批量提交 PDF 解析任务

**Given**: 用户准备好多个 PDF 文件  
**When**: 用户批量上传 5 个 PDF 文件  
**Then**: 
- 响应状态码应为 `202 Accepted`
- 响应体应包含 `tasks` 数组,包含所有任务信息
- 每个任务应有独立的 `task_id`
- 所有任务状态应为 `PENDING`
- 返回当前队列状态

**请求示例**:
```http
POST /api/v1/pdf/extract
Content-Type: multipart/form-data

files=@bp_1.pdf
files=@bp_2.pdf
files=@bp_3.pdf
user_id=user123
project_id=project456
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "550e8400-...",
        "source_filename": "bp_1.pdf",
        "task_status": "PENDING",
        "submitted_at": "2025-11-18T10:30:00Z"
      },
      {
        "task_id": "660e8400-...",
        "source_filename": "bp_2.pdf",
        "task_status": "PENDING",
        "submitted_at": "2025-11-18T10:30:01Z"
      }
    ],
    "queue_status": {
      "total_submitted": 3,
      "queue_size": 8,
      "active_tasks": 5
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:01Z"
  }
}
```

#### Scenario 1.2: 上传非 PDF 文件

**Given**: 用户尝试上传一个图片文件(.jpg)  
**When**: 用户提交文件  
**Then**: 
- 响应状态码应为 `400 Bad Request`
- 响应体应包含错误信息,说明文件类型不合法
- 文件不应被上传到 OSS
- 数据库不应创建新记录

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "文件类型不合法,仅支持 PDF 格式",
    "details": {
      "uploaded_type": "image/jpeg",
      "expected_type": "application/pdf"
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 1.3: 上传超大 PDF 文件

**Given**: 用户上传一个 80MB 的 PDF 文件  
**When**: 用户提交文件  
**Then**: 
- 响应状态码应为 `413 Payload Too Large`
- 响应体应包含错误信息,说明文件过大
- 文件不应被上传到 OSS

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "PDF 文件大小超出限制",
    "details": {
      "file_size_mb": 80,
      "max_size_mb": 50
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 1.4: 上传页数过多的 PDF

**Given**: 用户上传一个包含 150 页的 PDF 文件  
**When**: 系统验证文件后  
**Then**: 
- 响应状态码应为 `400 Bad Request`
- 响应体应包含错误信息,说明页数超出限制
- 文件不应被上传到 OSS

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "TOO_MANY_PAGES",
    "message": "PDF 页数超出限制",
    "details": {
      "page_count": 150,
      "max_pages": 100
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 1.5: 缺少必填参数

**Given**: 用户上传 PDF 但未提供 `user_id`  
**When**: 用户提交请求  
**Then**: 
- 响应状态码应为 `422 Unprocessable Entity`
- 响应体应包含验证错误信息

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "user_id",
        "message": "字段 user_id 为必填项"
      }
    ]
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

---

### 2. 查询 PDF 解析任务详情

**端点**: `GET /api/v1/pdf/extract/{task_id}`

#### Scenario 2.1: 查询成功完成的任务

**Given**: 存在一个状态为 `SUCCEEDED` 的任务  
**When**: 用户使用 `task_id` 查询任务详情  
**Then**: 
- 响应状态码应为 `200 OK`
- 响应体应包含完整的任务信息
- 响应体应包含 `extracted_info` 字段,包含所有提取的字段
- 响应体应包含 `extracted_info_url` 字段,指向 OSS 上的 JSON 文件
- 响应体应包含 `extracted_info_signed_url` 字段,提供临时签名访问链接
- `extracted_info` 应包含 15 个核心字段
- `completed_at` 字段应有值

**请求示例**:
```http
GET /api/v1/pdf/extract/550e8400-e29b-41d4-a716-446655440000
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_status": "SUCCEEDED",
    "model": "qwen3-vl-flash",
    "pdf_url": "https://oss.../original.pdf",
    "page_count": 15,
    "extracted_info": {
      "project_source": "张三",
      "project_contact": "李四",
      "contact_info": "13800138000",
      "company_name": "创新科技有限公司",
      "industry": "人工智能",
      "core_team": [
        {
          "name": "李四",
          "role": "CEO",
          "background": "清华大学计算机博士"
        }
      ],
      "core_product": "基于大模型的智能客服系统",
      "keywords": ["人工智能", "大模型", "企业服务"]
    },
    "extracted_info_url": "https://oss.../startup_bp_2025_extracted_info.json",
    "extracted_info_signed_url": "https://oss.../startup_bp_2025_extracted_info.json?signature=...",
    "submitted_at": "2025-11-18T10:30:00Z",
    "completed_at": "2025-11-18T10:30:45Z"
  },
  "metadata": {
    "timestamp": "2025-11-18T10:31:00Z",
    "processing_time": 45.2
  }
}
```

#### Scenario 2.2: 查询处理中的任务

**Given**: 存在一个状态为 `PROCESSING` 的任务  
**When**: 用户查询任务详情  
**Then**: 
- 响应状态码应为 `200 OK`
- `task_status` 应为 `PROCESSING`
- `extracted_info` 字段应为 `null`
- `completed_at` 字段应为 `null`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_status": "PROCESSING",
    "model": "qwen3-vl-flash",
    "pdf_url": "https://oss.../original.pdf",
    "page_count": 15,
    "extracted_info": null,
    "submitted_at": "2025-11-18T10:30:00Z",
    "started_at": "2025-11-18T10:30:05Z",
    "completed_at": null
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:20Z",
    "estimated_remaining": "25-40s"
  }
}
```

#### Scenario 2.3: 查询失败的任务

**Given**: 存在一个状态为 `FAILED` 的任务  
**When**: 用户查询任务详情  
**Then**: 
- 响应状态码应为 `200 OK`
- `task_status` 应为 `FAILED`
- 响应体应包含 `error` 字段,说明失败原因
- `extracted_info` 字段应为 `null`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_status": "FAILED",
    "model": "qwen3-vl-flash",
    "pdf_url": "https://oss.../original.pdf",
    "page_count": 15,
    "extracted_info": null,
    "error": {
      "type": "VLModelError",
      "message": "模型调用超时",
      "details": {
        "attempt": 3,
        "last_error": "Request timeout after 60s"
      }
    },
    "submitted_at": "2025-11-18T10:30:00Z",
    "completed_at": "2025-11-18T10:32:30Z"
  },
  "metadata": {
    "timestamp": "2025-11-18T10:33:00Z"
  }
}
```

#### Scenario 2.4: 查询不存在的任务

**Given**: 用户提供的 `task_id` 在数据库中不存在  
**When**: 用户查询任务详情  
**Then**: 
- 响应状态码应为 `404 Not Found`
- 响应体应包含错误信息

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "任务不存在",
    "details": {
      "task_id": "non-existent-id"
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 2.5: 查询其他用户的任务 (权限控制)

**Given**: 任务 A 属于用户 user1  
**And**: 当前请求用户为 user2  
**When**: user2 尝试查询任务 A  
**Then**: 
- 响应状态码应为 `403 Forbidden`
- 响应体应包含权限错误信息

**响应示例**:
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "无权访问此任务",
    "details": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

---

### 3. 列出 PDF 解析任务

**端点**: `GET /api/v1/pdf/extract`

#### Scenario 3.1: 列出所有任务(默认分页)

**Given**: 数据库中存在多个 PDF 解析任务  
**When**: 用户请求任务列表,不指定查询参数  
**Then**: 
- 响应状态码应为 `200 OK`
- 响应体应包含任务列表
- 默认返回第 1 页,每页 20 条记录
- 任务应按 `submitted_at` 降序排列
- 每个任务应包含基本信息: `task_id`, `company_name`, `industry`, `task_status`, `submitted_at`

**请求示例**:
```http
GET /api/v1/pdf/extract
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_name": "创新科技有限公司",
      "industry": "人工智能",
      "task_status": "SUCCEEDED",
      "submitted_at": "2025-11-18T10:30:00Z",
      "keywords": ["人工智能", "大模型"]
    },
    {
      "task_id": "660e8400-e29b-41d4-a716-446655440001",
      "company_name": "健康医疗科技",
      "industry": "医疗健康",
      "task_status": "PROCESSING",
      "submitted_at": "2025-11-18T09:15:00Z",
      "keywords": ["医疗", "AI诊断"]
    }
  ],
  "metadata": {
    "total": 156,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 3.2: 按行业筛选

**Given**: 数据库中存在不同行业的任务  
**When**: 用户指定 `industry=人工智能` 参数  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回的任务列表应只包含 `industry` 为 "人工智能" 的任务
- 分页信息应反映筛选后的总数

**请求示例**:
```http
GET /api/v1/pdf/extract?industry=人工智能&page=1&page_size=10
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_name": "创新科技有限公司",
      "industry": "人工智能",
      "task_status": "SUCCEEDED",
      "submitted_at": "2025-11-18T10:30:00Z"
    }
  ],
  "metadata": {
    "total": 45,
    "page": 1,
    "page_size": 10,
    "total_pages": 5,
    "filters": {
      "industry": "人工智能"
    },
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 3.3: 按状态筛选

**Given**: 数据库中存在不同状态的任务  
**When**: 用户指定 `status=SUCCEEDED` 参数  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回的任务列表应只包含 `task_status` 为 "SUCCEEDED" 的任务

**请求示例**:
```http
GET /api/v1/pdf/extract?status=SUCCEEDED&page=1&page_size=20
```

#### Scenario 3.4: 组合筛选

**Given**: 用户想查找特定行业且已完成的任务  
**When**: 用户指定 `industry=人工智能&status=SUCCEEDED` 参数  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回的任务应同时满足两个条件

**请求示例**:
```http
GET /api/v1/pdf/extract?industry=人工智能&status=SUCCEEDED&page=1&page_size=20
```

#### Scenario 3.5: 分页边界情况

**Given**: 总共有 156 条记录,每页 20 条  
**When**: 用户请求第 8 页  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回的数据应包含最后 16 条记录
- `total_pages` 应为 8
- `page` 应为 8

**请求示例**:
```http
GET /api/v1/pdf/extract?page=8&page_size=20
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    // ... 16 条记录
  ],
  "metadata": {
    "total": 156,
    "page": 8,
    "page_size": 20,
    "total_pages": 8,
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

#### Scenario 3.6: 请求超出范围的页码

**Given**: 总共只有 8 页数据  
**When**: 用户请求第 10 页  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回的数据应为空数组
- 元数据应正确显示总页数

**响应示例**:
```json
{
  "success": true,
  "data": [],
  "metadata": {
    "total": 156,
    "page": 10,
    "page_size": 20,
    "total_pages": 8,
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

---

### 4. 查询队列状态

**端点**: `GET /api/v1/pdf/queue/status`

#### Scenario 4.1: 查询当前队列状态

**Given**: 系统正在处理多个 PDF 任务  
**When**: 用户请求队列状态  
**Then**: 
- 响应状态码应为 `200 OK`
- 返回当前队列大小
- 返回活跃任务数
- 返回待处理任务数
- 返回最大并发数

**请求示例**:
```http
GET /api/v1/pdf/queue/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "queue_size": 12,
    "active_tasks": 5,
    "pending_tasks": 7,
    "max_concurrent": 5,
    "active_task_ids": [
      "550e8400-...",
      "660e8400-...",
      "770e8400-...",
      "880e8400-...",
      "990e8400-..."
    ]
  },
  "metadata": {
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

---

## 通用行为规范

### 响应格式

所有 API 响应应遵循统一格式:

```json
{
  "success": true | false,
  "data": { ... } | [ ... ],  // 成功时存在
  "error": { ... },           // 失败时存在
  "metadata": {
    "timestamp": "ISO 8601 格式时间戳",
    // ... 其他元数据
  }
}
```

### 错误码规范

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `INVALID_FILE_TYPE` | 400 | 文件类型不合法 |
| `FILE_TOO_LARGE` | 413 | 文件大小超出限制 |
| `TOO_MANY_PAGES` | 400 | PDF 页数超出限制 |
| `VALIDATION_ERROR` | 422 | 请求参数验证失败 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `PERMISSION_DENIED` | 403 | 无权访问 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `VL_MODEL_ERROR` | 500 | 模型调用失败 |
| `STORAGE_ERROR` | 500 | 存储服务错误 |

### 时间格式

所有时间戳应使用 ISO 8601 格式,包含时区信息:
```
2025-11-18T10:30:00Z
2025-11-18T18:30:00+08:00
```

### 分页参数

- `page`: 页码,从 1 开始,默认 1
- `page_size`: 每页记录数,默认 20,最大 100

### 排序参数

- `sort_by`: 排序字段,默认 `submitted_at`
- `order`: 排序顺序,`asc` 或 `desc`,默认 `desc`

---

## 字段提取规范

### 必填字段验证

以下字段为必填,提取结果中必须包含(可为空字符串,但不能缺失):
- `company_name`
- `industry`
- `core_team`
- `core_product`
- `keywords`

### 行业分类验证

`industry` 字段必须从预定义列表中选择:
```
["人工智能", "企业服务", "医疗健康", "教育培训", "金融科技", 
 "电子商务", "文化娱乐", "智能制造", "新能源", "生物科技", 
 "物联网", "区块链", "半导体", "新材料", "其他"]
```

如果提取的行业不在列表中,应自动映射为 "其他"。

### 团队成员格式

`core_team` 应为对象数组,每个对象包含:
```json
{
  "name": "必填,成员姓名",
  "role": "必填,职位",
  "background": "选填,背景描述"
}
```

至少应包含 1 个团队成员。

### 关键词要求

`keywords` 应为字符串数组:
- 最少 3 个关键词
- 最多 15 个关键词
- 自动去重
- 涵盖技术、团队、融资等维度

### 财务状态格式

`financial_status` 应为对象:
```json
{
  "current": "当前财务状况描述",
  "future": "未来财务规划描述"
}
```

两个字段均为可选。

---

## 性能要求

- **上传接口响应**: < 500ms (不含 OSS 上传时间)
- **查询接口响应**: < 200ms
- **列表接口响应**: < 300ms
- **PDF 处理总时长**: < 60s (15 页以内)

---

## 安全要求

- 所有接口应验证用户身份(JWT Token)
- 用户只能查询自己的任务
- OSS 签名 URL 应设置合理的过期时间(24小时)
- 上传的 PDF 应进行病毒扫描(可选)
- 应记录所有敏感操作的审计日志

---

**版本**: v1.0  
**最后更新**: 2025-11-18  
**维护者**: AI Assistant
