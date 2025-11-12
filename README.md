# 文档知识图谱提取工具

> 基于 RAG-Anything 论文思路的**双模态知识图谱提取系统**  
> 支持**文本 Pipeline** 和 **图片 Pipeline** 两条并行处理流程

**版本**: v1.4.1 | **更新**: 2025-11-12 | **状态**: 🎉 生产就绪

## 🌟 核心特性

### 📄 文本 Pipeline (v1.2+)
- ✅ 文档智能解析与文本提取
- ✅ 基于 LLM 的实体关系抽取（并行化处理，速度提升2-3倍）
- ✅ 智能实体去重与合并（相似度算法）
- ✅ 本体对齐到6+1核心类型（Company/Person/Technology/Signal/Product/TagConcept/Other）
- ✅ 双版本输出（raw + aligned）

### 🎨 图片 Pipeline (v1.4.1 - 2025-11-11)
- ✅ 三级智能过滤（表格图片 + 分辨率 + OCR文本长度）
- ✅ 上下文感知描述生成（使用 Qwen3-VL-Flash 多模态模型）
- ✅ 从图片描述中提取知识实体和关系
- ✅ 本体对齐到核心类型（与文本Pipeline共享OntologyAligner）
- ✅ 鲁棒JSON解析（自动修复特殊字符，100%成功率）
- ✅ 格式统一输出（与文本Pipeline完全一致，可直接合并）

### 🔗 系统集成
- 🌐 RESTful API 服务（基于 FastAPI）
- 📊 双版本知识图谱（细粒度原始数据 + 标准化对齐数据）
- 🎯 格式完全统一（文本和图片输出可直接合并）
- 🗄️ 支持持久化到 PostgreSQL + Neo4j（规划中）

## 📋 快速导航

| 使用方式 | 适用场景 | 跳转链接 |
|---------|---------|---------|
| 🌐 **RESTful API** | 远程调用、Web集成、多用户服务 | [API 使用指南](#-api-使用指南) |
| 🎨 **图片 Pipeline** | 图片内容理解、视觉知识提取 | [图片 Pipeline](#-图片-pipeline-使用) |
| 💻 **文本 Pipeline** | 文本内容提取、批量处理 | [文本 Pipeline](#-文本-pipeline-使用) |
| 📊 **架构设计** | 了解系统架构和数据流 | [架构概览](#-架构概览) |
| 📈 **测试结果** | 查看性能数据和测试报告 | [测试结果](#-测试结果-2025-11-11) |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MinerU 文档解析输出                        │
│                  *_content_list.json                         │
└────────────────┬────────────────────────────┬────────────────┘
                 │                            │
                 ▼                            ▼
    ┌────────────────────────┐   ┌────────────────────────┐
    │   文本 Pipeline        │   │   图片 Pipeline        │
    │  text_pipeline.py      │   │  image_pipeline.py     │
    └────────────────────────┘   └────────────────────────┘
                 │                            │
                 │  ┌──────────────────┐     │
                 │  │ OntologyAligner  │←────┤
                 │  │  (本体对齐器)    │     │
                 │  └──────────────────┘     │
                 │                            │
                 ▼                            ▼
    ┌────────────────────────┐   ┌────────────────────────┐
    │ *_text_kg_raw.json     │   │ *_image_kg_raw.json    │
    │ *_text_kg_aligned.json │   │ *_image_kg_aligned.json│
    └────────────────────────┘   └────────────────────────┘
                 │                            │
                 └────────────┬───────────────┘
                              ▼
                   ┌──────────────────────┐
                   │  统一格式知识图谱    │
                   │  (可直接合并)        │
                   └──────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │ PostgreSQL + Neo4j   │
                   │   (持久化存储)       │
                   └──────────────────────┘
```

## 🎯 快速开始

## 🎨 图片 Pipeline 使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# .env 文件
DASHSCOPE_API_KEY=your_dashscope_api_key
```

### 3. 基础用法

```bash
# 处理单个文件
python pipelines/image_pipeline.py "parsed/象量科技项目介绍20250825/auto/象量科技项目介绍20250825_content_list.json"

# 自定义输出目录
python pipelines/image_pipeline.py "path/to/content_list.json" --output-dir "output/images"

# 使用更强的模型
python pipelines/image_pipeline.py "path/to/content_list.json" --model qwen3-vl-plus

# 调整上下文窗口
python pipelines/image_pipeline.py "path/to/content_list.json" --context-window 3

# 自定义过滤参数
python pipelines/image_pipeline.py "path/to/content_list.json" \
    --ocr easyocr \
    --res-preset m \
    --min-text-len 15
```

### 4. Python 代码使用

```python
from pipelines import ImageKnowledgeGraphPipeline, ImagePipelineConfig

# 配置
config = ImagePipelineConfig(
    ocr_engine="auto",           # OCR 引擎: auto/pytesseract/easyocr/paddleocr/none
    res_preset="s",              # 分辨率预设: s(28万)/m(60万)/l(120万)/off
    min_text_len=10,             # 最小文本长度
    context_window=2,            # 上下文窗口大小
    multimodal_model="qwen3-vl-flash",  # 多模态模型
    temperature=0.1
)

# 运行
pipeline = ImageKnowledgeGraphPipeline(config)
pipeline.run("path/to/content_list.json")
```

### 5. 处理流程

```
输入: content_list.json (MinerU 输出)
  ↓
【阶段零】表格图片识别
  ├─ 收集所有 type="table" 的 img_path
  └─ 标记为黑名单，不进入后续处理
  ↓
【阶段一】图片过滤（三级）
  ├─ 表格过滤: 排除黑名单中的图片
  ├─ 分辨率过滤: 像素数 < 阈值 (s=28万/m=60万/l=120万)
  └─ OCR文本过滤: 文字数 < min_text_len (默认10)
  ↓
【阶段二】上下文感知描述生成
  ├─ 提取图片标题 (image_caption + footnote)
  ├─ 查找最近的章节标题
  ├─ 提取前后文本段落 (context_window=2)
  ├─ 调用 Qwen3-VL-Flash 生成描述
  ├─ 鲁棒JSON解析 (自动修复反斜杠等特殊字符)
  └─ 生成 entity_name, type, description
  ↓
【阶段三】知识实体提取与对齐
  ├─ 使用 qwen-plus 从描述中提取实体和关系
  ├─ 添加 source_image 和 page_idx 字段
  ├─ 调用 OntologyAligner 对齐到核心类型
  └─ 映射到 Company/Technology/Signal/Product/TagConcept
  ↓
输出（两个独立文件）:
  ├─ *_image_kg_raw.json (图片描述 + 原始实体)
  └─ *_image_kg_aligned.json (对齐后的知识图谱)
```

### 6. 命令行参数

```
参数说明:
  input                输入的 content_list.json 路径
  --output-dir DIR     输出目录（默认与输入文件同目录）
  --model MODEL        多模态模型名称（默认: qwen3-vl-flash）
  --context-window N   上下文窗口大小（默认: 2）
  --ocr ENGINE         OCR 引擎（auto/pytesseract/easyocr/paddleocr/none）
  --res-preset PRESET  分辨率预设（s/m/l/off，默认: s）
  --min-text-len N     最小文本长度（默认: 10）
  --verbose            显示详细日志
```

### 7. 输出格式

**文件1: *_image_kg_raw.json** (图片描述 + 原始实体):
```json
{
  "metadata": {
    "source_file": "path/to/content_list.json",
    "total_images": 11,
    "total_entities": 75,
    "total_relations": 67,
    "entity_types": ["Company", "Technology", "Product", ...],
    "relation_types": ["uses_technology", "part_of", ...],
    "filtered_stats": {
      "total_images": 24,
      "collected_table_images": 5,
      "filtered_by_resolution": 9,
      "filtered_by_text_length": 4,
      "valid_images": 11
    },
    "build_time": "2025-11-11T17:20:40"
  },
  "images": [
    {
      "img_path": "images/097c10...bdce8b.jpg",
      "page_idx": 4,
      "entity_name": "数字技术赋能股权投资阶段演进图",
      "type": "流程图",
      "description": "展示从PC时代到AGI时代，二级市场与一级市场在投资逻辑上的演变...",
      "context": {
        "image_caption": "无",
        "nearest_title": "数字技术赋能股权投资的各阶段",
        "nearby_text": "..."
      }
    }
  ],
  "entities": {  // ⚠️ 字典格式，key=实体名
    "大智慧": {
      "name": "大智慧",
      "type": "Company",
      "description": "PC时代的金融信息服务提供商",
      "attributes": {"industry": "金融科技"},
      "source_image": "images/097c10...bdce8b.jpg",
      "page_idx": 4
    }
  },
  "relations": [
    {
      "source_entity": "大智慧",
      "target_entity": "PC时代",
      "relation_type": "part_of",
      "description": "...",
      "confidence": 1.0
    }
  ]
}
```

**文件2: *_image_kg_aligned.json** (对齐后的知识图谱):
```json
{
  "metadata": {
    "source_file": "path/to/content_list.json",
    "total_aligned_entities": 80,
    "total_aligned_relations": 67,
    "aligned_entity_types": ["Company", "Technology", "Signal", "Product", "TagConcept"],
    "aligned_relation_types": ["uses_technology", "part_of", ...],
    "ontology_version": "v1.2.1",
    "data_source": "image_pipeline",
    "build_time": "2025-11-11T17:20:40"
  },
  "aligned_entities": {  // ⚠️ 字典格式，key=实体名
    "大智慧": {
      "name": "大智慧",
      "core_type": "Company",  // ⭐ 对齐后的核心类型
      "alt_names": [],
      "description": "PC时代的金融信息服务提供商",
      "industry": "金融科技",
      "stage": "上市公司",
      "source_image": "images/097c10...bdce8b.jpg",  // ⭐ 保留图片来源
      "page_idx": 4,
      "source_entities": ["大智慧"],
      "confidence": 1.0,
      "provenance": []
    }
  },
  "aligned_relations": [
    {
      "source_entity": "大智慧",
      "target_entity": "PC时代",
      "core_relation_type": "part_of",
      "description": "...",
      "confidence": 1.0,
      "source_relations": ["part_of"],
      "provenance": []
    }
  ]
}
```

**关键特点**:
- ✅ **格式统一**: entities 为字典结构 (key=实体名)，与text_pipeline完全一致
- ✅ **来源追溯**: 每个实体都包含 `source_image` 和 `page_idx`
- ✅ **可直接合并**: 与text_pipeline的输出可以直接合并entities字典

## 💻 文本 Pipeline 使用

详见 [README_PIPELINE.md](README_PIPELINE.md) 获取完整的文本Pipeline使用文档。

## 🌐 API 使用指南

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置:

```bash
cp .env.example .env
# 编辑 .env 文件,填入你的 DASHSCOPE_API_KEY
```

### 3. 启动 API 服务

**Windows**:
```cmd
run_api.bat
```

**Linux/Mac**:
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问 API 文档

启动后访问:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

### 5. API 使用示例

#### Python 调用

```python
import requests

# 上传文件提取知识图谱
with open('document.json', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/extract',
        files={'file': ('doc.json', f, 'application/json')},
        params={
            'chunk_size': 512,
            'max_workers': 3
        }
    )

if response.status_code == 200:
    result = response.json()
    print(f"提取了 {result['data']['summary']['total_raw_entities']} 个实体")
elif response.status_code == 202:
    # 异步任务
    task_id = response.json()['data']['task_id']
    print(f"任务ID: {task_id}")
    
    # 查询任务状态
    status_resp = requests.get(f'http://localhost:8000/api/v1/tasks/{task_id}')
    print(status_resp.json())
```

详细示例见: `examples/api_usage.py`

#### cURL 调用

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 提取知识图谱
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@document.json" \
  -F "chunk_size=512" \
  -F "max_workers=3"

# 查询任务状态
curl http://localhost:8000/api/v1/tasks/{task_id}
```

详细示例见: `examples/curl_examples.sh`

### API 端点说明

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查,返回服务状态 |
| `/api/v1/extract` | POST | 上传文件提取知识图谱 |
| `/api/v1/tasks/{task_id}` | GET | 查询异步任务状态 |

### 同步 vs 异步处理

- **小文件** (< 10MB, < 50页): 同步返回结果 (status 200)
- **大文件** (> 10MB 或 > 50页): 返回 task_id,异步处理 (status 202)

## 📦 主要功能（文本+图片）

### 文本 Pipeline
- ✅ 文档解析与动态分组（按字符长度智能分组）
- ✅ 并行实体提取（多线程LLM调用，速度提升2-3倍）
- ✅ 智能实体去重与合并（相似度算法）
- ✅ 关系端点规范化
- ✅ 本体对齐到核心类型
- ✅ 双版本知识图谱输出（raw + aligned）

### 图片 Pipeline
- ✅ 三级智能过滤（表格/分辨率/OCR文本）
- ✅ 上下文感知描述生成（Qwen3-VL-Flash）
- ✅ 鲁棒JSON解析（自动修复特殊字符）
- ✅ 图片实体提取与关系抽取
- ✅ 本体对齐（共享OntologyAligner）
- ✅ 格式统一输出（与文本Pipeline完全一致）

### 共享能力
- 🎯 6+1核心实体类型：Company/Person/Technology/Signal/Product/TagConcept/Other
- 📊 双版本输出：细粒度原始数据 + 标准化对齐数据
- 🔗 格式统一：文本和图片输出可直接合并
- 🌐 RESTful API：统一接口访问
- 📈 完整溯源：provenance证据链（来源、时间、置信度）

## 🎯 核心实体类型

| 类型 | 说明 | 用途 | 支持来源 |
|-----|------|------|---------|
| `Company` | 公司/组织 | 投资标的、可比公司 | 文本+图片 |
| `Person` | 人物 | 创始人、高管 | 文本+图片 |
| `Technology` | 技术/概念 | 技术路线、算法 | 文本+图片 |
| `Signal` | 信号 | 指标、趋势、数据 | 文本+图片 |
| `Product` | 产品 | 产品/服务 | 文本+图片 |
| `TagConcept` | 赛道/标签 | 细分领域、行业分类 | 文本+图片 |
| `Event` | 事件 | 融资、新闻、政策 | 文本 |
| `Other` | 其他 | Fallback类型 | 文本+图片 |

## 📚 文档资源

- 📖 **完整使用文档**: [README_PIPELINE.md](README_PIPELINE.md)
  - 文本Pipeline详细说明
  - 图片Pipeline详细说明
  - 所有配置参数说明
  - 命令行使用示例
- 📝 **变更日志**: `docs/CHANGELOG_*.md`
- 🎯 **本体设计**: `docs/ontology构建.md`
- 🏗️ **架构文档**: `docs/RAGAnything.md`

## 🚀 路线图

### ✅ 已完成 (v1.4.1)
- ✅ 文本Pipeline（并行处理、本体对齐）
- ✅ 图片Pipeline（多模态理解、实体提取）
- ✅ FastAPI REST API
- ✅ 双版本输出（raw + aligned）
- ✅ 格式统一（文本+图片可合并）

### 🔜 短期计划 (v1.5)
- [ ] 知识图谱合并工具（自动合并文本和图片KG）
- [ ] 表格内容提取增强
- [ ] 批处理优化与进度保存
- [ ] 单元测试覆盖率提升

### 🎯 中期规划 (v2.0)
- [ ] PostgreSQL + Neo4j持久化
- [ ] 实体去重与链接（跨文档）
- [ ] 增量更新机制
- [ ] Web可视化界面

### 🌟 长期愿景 (v3.0)
- [ ] 混合检索系统（向量+图谱）
- [ ] 智能问答Agent
- [ ] 完整RAG解决方案

## ⚠️ 注意事项

1. **API Key**: 需要配置有效的DASHSCOPE_API_KEY
2. **输入格式**: 要求JSON格式，包含`type`和`page_idx`字段
3. **内存占用**: 大文档处理时注意内存使用
4. **LLM调用**: 每页独立调用LLM，注意成本控制

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发规范
- 遵循Google Python Style Guide
- 添加类型注解
- 编写完整的docstring
- 提交前运行测试

## 📄 许可证

本项目采用 MIT 许可证

## 📞 联系方式

- 提交Issue: [GitHub Issues]
- 技术讨论: [Discussions]
- 邮件联系: [项目维护者]

## 📊 测试结果 (2025-11-11)

### 图片 Pipeline 测试
- ✅ **处理成功率**: 11/11 (100%)
- ✅ **JSON解析成功率**: 11/11 (100%，含1次自动修复)
- ✅ **表格图片识别**: 5张正确排除
- ✅ **过滤统计**: 24张原始 → 11张有效 (9张分辨率 + 4张文本)
- ✅ **实体提取**: 80个对齐实体，67个关系
- ✅ **实体类型分布**: Company(21) + Technology(20) + Signal(21) + Product(9) + TagConcept(9)

### 关键优化
1. **鲁棒JSON解析**: 自动检测并修复反斜杠 `\` → `/`
2. **实体对齐成功**: OntologyAligner正确加载，80个实体映射到核心类型
3. **格式完全统一**: entities从列表改为字典，与text_pipeline一致
4. **日志优化**: 参考text_pipeline，保持简洁清晰风格
5. **移除外部依赖**: image_filter.py整合到pipeline.py，自包含OCR

---

**版本**: v1.4.1  
**最后更新**: 2025-11-12  
**状态**: 🎉 生产就绪 (文本+图片双Pipeline)  
**基于**: RAG-Anything论文数据处理思路

---

**快速链接**:
- 📖 [完整使用文档](README_PIPELINE.md)
- 🏗️ [OpenSpec项目规范](openspec/project.md)  
- 🎨 [图片Pipeline变更提案](openspec/changes/add-image-pipeline/proposal.md)
