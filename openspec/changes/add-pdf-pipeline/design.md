# 设计: PDF 商业计划书智能解析管道

## 概述

本文档描述 PDF 商业计划书解析功能的详细技术设计,包括架构、数据流、关键组件和实现细节。

## 架构设计

### 系统架构图

```
┌─────────────┐
│   前端 UI   │
│  (React)    │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────────────────────────────────────────┐
│         FastAPI 后端                             │
│  ┌────────────────────────────────────────────┐ │
│  │  PDF Extract Routes                        │ │
│  │  - POST /api/v1/pdf/extract (批量支持)     │ │
│  │  - GET  /api/v1/pdf/extract/{id}          │ │
│  │  - GET  /api/v1/pdf/extract (带过滤)       │ │
│  └────────────┬───────────────────────────────┘ │
│               │                                  │
│  ┌────────────↓───────────────────────────────┐ │
│  │  Async Task Queue (asyncio)                │ │
│  │  - 任务优先级队列                           │ │
│  │  - 并发控制 (max 5)                        │ │
│  │  - 任务状态管理                            │ │
│  └────────────┬───────────────────────────────┘ │
│               │                                  │
│  ┌────────────↓───────────────────────────────┐ │
│  │  PDF Pipeline Service                      │ │
│  │  - PDF 转图片 (可配置DPI)                  │ │
│  │  - 图片上传 OSS                            │ │
│  │  - 调用 Qwen VL (实时API)                 │ │
│  │  - 结果验证与清洗                          │ │
│  │  - JSON 上传 OSS                          │ │
│  └────────────┬───────────────────────────────┘ │
└───────────────┼─────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    ↓           ↓           ↓
┌────────┐  ┌──────┐  ┌──────────┐
│  OSS   │  │ 通义 │  │PostgreSQL│
│ Storage│  │千问VL│  │ Database │
└────────┘  └──────┘  └──────────┘
```

### 处理流程

```
1. 上传阶段
   用户上传 PDF
        ↓
   后端接收并验证
        ↓
   上传原始 PDF 到 OSS
        ↓
   创建数据库记录 (PENDING)
        ↓
   返回 task_id

2. 转换阶段 (异步)
   从 OSS 下载 PDF
        ↓
   使用 pdf2image 转换
   (DPI=300, format=JPEG)
        ↓
   压缩图片 (如果 >5MB)
        ↓
   上传页面图片到 OSS
        ↓
   更新状态为 PROCESSING

3. 提取阶段
   构建提取 Prompt
        ↓
   调用 Qwen3-VL-Flash
   - vl_high_resolution_images=True
   - 传入所有页面图片
        ↓
   解析 JSON 响应
        ↓
   字段验证与清洗

4. 存储阶段
   生成标准化 JSON
        ↓
   上传到 OSS
        ↓
   更新数据库记录
        ↓
   状态设为 SUCCEEDED

5. 查询阶段
   客户端轮询或主动查询
        ↓
   返回提取结果
        ↓
   生成临时签名 URL
```

## 核心组件设计

### 0. Huey 任务队列配置 (新增)

**职责**: 使用 Huey 框架管理分布式 PDF 处理任务队列

```python
# pipelines/tasks.py
from huey import RedisHuey
import os

# 初始化 Huey
huey = RedisHuey(
    name=os.getenv('HUEY_QUEUE_NAME', 'pdf-tasks'),
    url=os.getenv('HUEY_REDIS_URL', 'redis://localhost:6379'),
    immediate=os.getenv('HUEY_IMMEDIATE', 'false').lower() == 'true'
)

@huey.task()
def process_pdf_task(task_id: str):
    """
    异步处理 PDF 任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        处理结果
    """
    from pipelines.pdf_extraction_service import PDFExtractionService
    
    service = PDFExtractionService()
    try:
        service.process_pdf(task_id)
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        raise  # Huey 会自动重试

# FastAPI 中的使用
# api/pdf/routes.py
from pipelines.tasks import process_pdf_task

async def submit_extraction(...):
    # ... 上传 PDF、入库等操作 ...
    
    # 提交任务到 Huey 队列
    process_pdf_task(task_id)  # 异步执行
    
    return task_id
```

**特点**：
- ✅ 任务持久化到 Redis
- ✅ 支持独立 worker 进程（可多台部署）
- ✅ 内置重试机制（失败自动重试 3 次）
- ✅ 内置死信队列（失败任务保留）
- ✅ 支持任务优先级
- ✅ 支持定时任务（cron）
- ✅ 生产级别稳定性

**启动方式**：
```bash
# 启动 Huey worker（5 个线程）
huey_consumer pipelines.tasks.huey -w 5 -k thread

# 或使用进程（多核利用）
huey_consumer pipelines.tasks.huey -w 5 -k process
```

### 1. PDFExtractionService

**职责**: PDF 处理与信息提取的核心服务

```python
class PDFExtractionService:
    """PDF 商业计划书提取服务"""
    
    def __init__(self):
        self.vl_client = QwenVLClient()
        self.storage_client = OSSStorageClient()
        
        # 从环境变量读取配置
        self.max_size_mb = int(os.getenv('PDF_MAX_SIZE_MB', 50))
        self.max_pages = int(os.getenv('PDF_MAX_PAGES', 100))
        self.dpi = int(os.getenv('PDF_CONVERSION_DPI', 300))
        self.image_max_size_mb = int(os.getenv('PDF_IMAGE_MAX_SIZE_MB', 10))
        
    async def submit_extraction(
        self,
        pdf_path: Path,
        user_id: str,
        project_id: str,
        source_filename: str
    ) -> str:
        """
        提交 PDF 提取任务
        
        Returns:
            task_id: 任务唯一标识
        """
        
    async def process_pdf(self, task_id: str):
        """
        处理 PDF 文件（异步）
        
        流程:
        1. 下载 PDF
        2. 转换为图片
        3. 上传图片
        4. 调用 VL 模型
        5. 保存结果
        """
        
    def _pdf_to_images(self, pdf_path: Path) -> List[Path]:
        """将 PDF 转换为高清图片"""
        
    def _compress_image(self, image_path: Path, max_size_mb: int = 5) -> Path:
        """压缩图片到指定大小"""
        
    async def _extract_info(self, image_urls: List[str]) -> dict:
        """调用 Qwen VL 提取信息"""
        
    def _validate_extracted_info(self, data: dict) -> dict:
        """验证和清洗提取的数据"""
```

### 2. QwenVLClient

**职责**: 封装 Qwen VL API 调用

```python
class QwenVLClient:
    """通义千问 VL 客户端"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "qwen3-vl-flash"
        self.extraction_prompt = EXTRACTION_PROMPT
        
    async def extract_from_images(
        self,
        image_urls: List[str],
        custom_fields: Optional[Dict] = None
    ) -> dict:
        """
        从图片列表中提取结构化信息
        
        Args:
            image_urls: 页面图片 URL 列表
            custom_fields: 自定义提取字段（可选）
            
        Returns:
            提取的结构化信息
        """
        messages = self._build_messages(image_urls)
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            extra_body={
                'enable_thinking': False  # 关闭思考模式加快速度
            },
            temperature=0.1  # 降低随机性
        )
        
        result = completion.choices[0].message.content
        return self._parse_json_response(result)
        
    def _build_messages(self, image_urls: List[str]) -> List[dict]:
        """构建 API 请求消息"""
        content = []
        
        # 添加所有图片
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
        
        # 添加提取指令
        content.append({
            "type": "text",
            "text": self.extraction_prompt
        })
        
        return [{"role": "user", "content": content}]
        
    def _parse_json_response(self, response: str) -> dict:
        """解析模型返回的 JSON"""
        # 尝试提取 JSON（可能包含额外文字）
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("无法从响应中提取 JSON")
```

### 3. 数据验证器

**职责**: 验证和标准化提取的数据

```python
class ExtractionValidator:
    """提取数据验证器"""
    
    REQUIRED_FIELDS = [
        'company_name',
        'industry',
        'core_team',
        'core_product',
        'keywords'
    ]
    
    VALID_INDUSTRIES = [
        "人工智能", "企业服务", "医疗健康", "教育培训",
        "金融科技", "电子商务", "文化娱乐", "智能制造",
        "新能源", "生物科技", "物联网", "区块链",
        "半导体", "新材料", "其他"
    ]
    
    def validate(self, data: dict) -> Tuple[bool, List[str]]:
        """
        验证提取的数据
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # 检查必填字段
        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f"缺少必填字段: {field}")
        
        # 验证行业
        if data.get('industry') not in self.VALID_INDUSTRIES:
            errors.append(f"无效的行业分类: {data.get('industry')}")
            
        # 验证团队成员
        if not isinstance(data.get('core_team'), list):
            errors.append("core_team 必须是数组")
        elif len(data.get('core_team', [])) < 1:
            errors.append("至少需要 1 个核心团队成员")
            
        # 验证关键词
        if not isinstance(data.get('keywords'), list):
            errors.append("keywords 必须是数组")
        elif len(data.get('keywords', [])) < 3:
            errors.append("至少需要 3 个关键词")
            
        return len(errors) == 0, errors
        
    def clean(self, data: dict) -> dict:
        """清洗和标准化数据"""
        cleaned = {}
        
        # 字符串字段去除首尾空格
        for field in ['company_name', 'industry', 'core_product', etc.]:
            if field in data and isinstance(data[field], str):
                cleaned[field] = data[field].strip()
        
        # 标准化行业分类
        if data.get('industry') not in self.VALID_INDUSTRIES:
            cleaned['industry'] = "其他"
        
        # 确保数组字段是列表
        if 'keywords' in data:
            cleaned['keywords'] = list(set(data['keywords']))[:15]  # 去重，最多15个
            
        return {**data, **cleaned}
```

### 4. 数据库操作

```python
async def create_pdf_extraction_task(
    task_id: str,
    pdf_url: str,
    user_id: str,
    project_id: str,
    source_filename: str
) -> dict:
    """创建 PDF 提取任务记录"""
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pdf_extraction_tasks (
                    task_id, task_status, model, pdf_url, pdf_object_key,
                    user_id, project_id, source_filename, submitted_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *
                """,
                (task_id, 'PENDING', 'qwen3-vl-flash', pdf_url, 
                 pdf_object_key, user_id, project_id, source_filename)
            )
            return await cur.fetchone()

async def update_extraction_result(
    task_id: str,
    extracted_info: dict,
    extracted_info_url: str,
    page_count: int
):
    """更新提取结果"""
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE pdf_extraction_tasks 
                SET task_status = 'SUCCEEDED',
                    extracted_info = %s,
                    extracted_info_url = %s,
                    page_count = %s,
                    company_name = %s,
                    industry = %s,
                    project_contact = %s,
                    keywords = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE task_id = %s
                """,
                (Json(extracted_info), extracted_info_url, page_count,
                 extracted_info.get('company_name'),
                 extracted_info.get('industry'),
                 extracted_info.get('project_contact'),
                 extracted_info.get('keywords'),
                 task_id)
            )
```

## Prompt 工程

### 核心提取 Prompt

```python
EXTRACTION_PROMPT = """
请仔细分析这份商业计划书的所有页面，提取以下字段信息。

**重要提示**:
1. 严格按照 JSON 格式输出
2. 如果某字段在文档中未找到，设为 null
3. 不要输出任何 JSON 之外的解释文字
4. 确保所有字符串使用双引号

**提取字段**:
```json
{
  "project_contact": "项目联系人或创始人的完整姓名",
  "contact_info": "电话号码或邮箱地址（优先电话）",
  "project_leader": "项目负责人（如果与联系人不同则填写，否则为null）",
  "company_name": "公司的完整注册名称",
  "company_address": "公司注册地址或主要办公地址",
  "industry": "从以下列表选择最匹配的行业：人工智能、企业服务、医疗健康、教育培训、金融科技、电子商务、文化娱乐、智能制造、新能源、生物科技、物联网、区块链、半导体、新材料、其他",
  "core_team": [
    {
      "name": "成员完整姓名",
      "role": "职位或角色（如CEO、CTO）",
      "background": "教育背景和工作经历的简要总结"
    }
  ],
  "core_product": "核心产品或服务的详细描述（100-200字）",
  "core_technology": "核心技术、技术优势或专利情况",
  "competition_analysis": "竞争格局分析，包括主要竞品和差异化优势",
  "market_size": "目标市场规模、增长趋势和市场机会",
  "financial_status": {
    "current": "当前财务状况（营收、利润、用户数、增长率等）",
    "future": "未来1-3年的财务规划或预测"
  },
  "financing_status": "已完成的融资轮次、金额、投资方，以及本轮融资需求",
  "keywords": ["关键词1", "关键词2", "关键词3", "..."]
}
```

**关键词提取要求**:
- 提取 5-10 个关键词
- 包括: 技术类关键词(如"大模型"、"区块链")
- 包括: 团队背景关键词(如"清华博士"、"Google前员工")
- 包括: 融资相关关键词(如"红杉投资"、"A轮"、"估值")
- 包括: 行业特征关键词

**核心团队提取要求**:
- 至少提取 2-3 个核心成员
- 优先提取 CEO、CTO、CFO、CPO 等高管
- background 字段要包含学历和工作经历

现在请开始提取，只输出 JSON，不要有任何其他内容。
"""
```

### Prompt 优化策略

1. **明确输出格式**: 要求严格的 JSON 格式
2. **提供示例**: 在字段说明中包含示例值
3. **分级提示**: 标注必填/选填字段
4. **约束输出**: 指定字符数范围、列表长度
5. **上下文提示**: 强调"综合所有页面"

## 错误处理

### 错误类型与处理

```python
class PDFExtractionError(Exception):
    """PDF 提取错误基类"""
    pass

class PDFConversionError(PDFExtractionError):
    """PDF 转换失败"""
    # 处理: 记录错误，返回 FAILED 状态
    
class VLModelError(PDFExtractionError):
    """VL 模型调用失败"""
    # 处理: 重试 3 次，仍失败则返回 FAILED
    
class ValidationError(PDFExtractionError):
    """数据验证失败"""
    # 处理: 记录哪些字段验证失败，状态为 PARTIAL_SUCCESS

# 重试装饰器
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(VLModelError)
)
async def extract_with_retry(image_urls: List[str]) -> dict:
    """带重试的提取功能"""
    pass
```

### 错误记录

```python
{
  "error": {
    "type": "VLModelError",
    "message": "模型调用超时",
    "details": {
      "attempt": 3,
      "last_error": "Request timeout after 60s"
    },
    "timestamp": "2025-11-18T10:30:00Z"
  }
}
```

## 性能优化

### 1. 图片压缩策略

```python
def optimize_image(image_path: Path, target_size_mb: int = 5) -> Path:
    """
    优化图片大小
    
    策略:
    1. 如果 < 5MB: 不处理
    2. 如果 5-10MB: 调整质量到 85%
    3. 如果 > 10MB: 先缩放到 2560px，再调整质量
    """
    from PIL import Image
    
    img = Image.open(image_path)
    file_size_mb = image_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb < target_size_mb:
        return image_path
        
    # 缩放策略
    if max(img.size) > 2560:
        ratio = 2560 / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # 质量调整
    quality = 85 if file_size_mb < 10 else 75
    output_path = image_path.with_suffix('.opt.jpg')
    img.save(output_path, 'JPEG', quality=quality, optimize=True)
    
    return output_path
```

### 2. 批量处理

```python
async def process_batch(task_ids: List[str], batch_size: int = 5):
    """批量处理多个 PDF 任务"""
    for i in range(0, len(task_ids), batch_size):
        batch = task_ids[i:i+batch_size]
        tasks = [process_pdf(tid) for tid in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. 缓存策略

```python
# OSS 图片 URL 缓存 24 小时
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_page_image_url(task_id: str, page_num: int) -> str:
    """获取页面图片 URL（带缓存）"""
    return storage_client.get_signed_url(
        f"pdf/{task_id}/pages/page_{page_num}.jpg",
        expires=86400
    )
```

## 安全考虑

### 1. 文件验证

```python
def validate_pdf(file_path: Path) -> bool:
    """验证 PDF 文件安全性"""
    
    # 检查文件大小 (< 50MB)
    if file_path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("PDF 文件过大")
    
    # 检查 MIME 类型
    import magic
    mime = magic.from_file(file_path, mime=True)
    if mime != 'application/pdf':
        raise ValueError("非法的文件类型")
    
    # 检查页数 (< 100 页)
    import pypdf
    with open(file_path, 'rb') as f:
        pdf = pypdf.PdfReader(f)
        if len(pdf.pages) > 100:
            raise ValueError("PDF 页数过多")
    
    return True
```

### 2. 敏感信息处理

```python
def sanitize_extracted_info(data: dict) -> dict:
    """清理敏感信息"""
    
    # 脱敏电话号码
    if 'contact_info' in data:
        data['contact_info'] = mask_phone(data['contact_info'])
    
    # 删除可能的邮箱地址
    # ...
    
    return data
```

## 监控与日志

### 关键指标

```python
# Prometheus 指标
pdf_extraction_total = Counter('pdf_extraction_total', '总提取任务数')
pdf_extraction_success = Counter('pdf_extraction_success', '成功任务数')
pdf_extraction_failed = Counter('pdf_extraction_failed', '失败任务数')
pdf_extraction_duration = Histogram('pdf_extraction_duration_seconds', '处理时长')
pdf_page_count = Histogram('pdf_page_count', 'PDF 页数分布')
vl_token_usage = Counter('vl_token_usage', 'VL Token 使用量', ['type'])
```

### 日志格式

```python
logger.info(
    "PDF extraction completed",
    extra={
        "task_id": task_id,
        "page_count": 15,
        "duration_ms": 45200,
        "token_usage": {"input": 75000, "output": 2000},
        "company_name": "创新科技",
        "industry": "人工智能"
    }
)
```

## 测试策略

### 单元测试

```python
@pytest.mark.asyncio
async def test_pdf_to_images():
    """测试 PDF 转图片功能"""
    service = PDFExtractionService()
    images = service._pdf_to_images(Path("test_data/sample.pdf"))
    
    assert len(images) == 5  # 5页PDF
    assert all(img.exists() for img in images)
    
@pytest.mark.asyncio
async def test_extraction_validation():
    """测试数据验证"""
    validator = ExtractionValidator()
    
    valid_data = {...}  # 完整数据
    is_valid, errors = validator.validate(valid_data)
    assert is_valid
    assert len(errors) == 0
    
    invalid_data = {"company_name": ""}  # 缺少必填字段
    is_valid, errors = validator.validate(invalid_data)
    assert not is_valid
    assert len(errors) > 0
```

### 集成测试

```python
@pytest.mark.integration
async def test_end_to_end_extraction():
    """端到端测试"""
    # 1. 上传 PDF
    task_id = await submit_extraction("test.pdf", "user1", "proj1")
    
    # 2. 等待处理完成
    await asyncio.sleep(60)
    
    # 3. 查询结果
    result = await get_extraction_result(task_id)
    
    assert result['task_status'] == 'SUCCEEDED'
    assert result['company_name'] is not None
    assert len(result['keywords']) >= 5
```

## 部署配置

### 环境变量

```bash
# Qwen VL API
DASHSCOPE_API_KEY=sk-xxx

# OSS 存储
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket
OSS_PDF_PREFIX=gold/userUploads

# PDF 处理限制 (根据官方文档)
PDF_MAX_SIZE_MB=50              # 建议 < 50MB (官方无明确限制)
PDF_MAX_PAGES=100               # 自定义限制,防止处理时间过长
PDF_CONVERSION_DPI=300          # 200-300 适中,过高影响性能
PDF_IMAGE_MAX_SIZE_MB=10        # 官方限制:单图 < 10MB

# VL 模型参数
VL_HIGH_RESOLUTION_MODE=false   # 高分辨率模式,手动可改为 true
VL_MAX_TOKENS=4096              # 最大输出 tokens
VL_TEMPERATURE=0.1              # 降低随机性,提高一致性

# 异步队列配置
PDF_MAX_CONCURRENT_TASKS=5      # 最大并发数 (避免过载)
PDF_QUEUE_SIZE=100              # 队列最大长度
PDF_TASK_TIMEOUT=300            # 单任务超时时间(秒)

# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db
```

### Docker 镜像

```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# ...
```

---

**版本**: v1.0  
**最后更新**: 2025-11-18  
**作者**: AI Assistant
