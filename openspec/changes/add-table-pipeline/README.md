# add-table-pipeline - 表格处理 Pipeline

## 📋 提案概述

为知识图谱提取系统添加**表格处理 Pipeline**，实现从 MinerU 解析的表格数据中自动提取知识实体。

**核心特点**：
- 🎯 **无需 VL 模型**：直接处理已识别的 HTML 表格
- 📊 **重点提取 Signal 类实体**：数据指标（营收、用户数、增长率等）
- 🔗 **格式统一**：与 text/image pipeline 输出完全一致
- ⚡ **成本优化**：表格内容已识别，无需昂贵的多模态模型

## 📁 文件结构

```
add-table-pipeline/
├── README.md        # 本文件
├── proposal.md      # 详细提案文档
├── tasks.md         # 实施任务清单
└── design.md        # 技术设计文档
```

## 🎯 核心目标

1. **补充知识来源**：形成文本+图片+表格的三模态知识图谱
2. **提取数据指标**：自动提取 Signal 类实体（营收、用户数、ARPU 等）
3. **格式统一输出**：与现有 Pipeline 保持一致，可直接合并

## 📊 状态追踪

- **状态**: Draft - 草案
- **优先级**: P1 - 高优先级
- **预计工作量**: 3-5天
- **创建日期**: 2025-11-12

## 🔄 处理流程

```
输入: content_list.json
  ↓
收集与过滤 (type="table")
  ↓
表格描述生成 (qwen-plus-latest)
  ↓
实体提取与对齐 (重点: Signal类)
  ↓
输出: *_table_raw.json + *_table_kg_aligned.json
```

## 📚 快速链接

- [详细提案](./proposal.md) - 完整的需求和技术方案
- [任务清单](./tasks.md) - 实施步骤和时间规划
- [技术设计](./design.md) - 架构和组件设计

## 🔗 相关资源

- **参考实现**: `pipelines/image_pipeline.py`
- **共享组件**: `text_pipeline.OntologyAligner`
- **外部源码**: `raganything/modalprocessors.py` - TableModalProcessor

## 📝 下一步

1. 评审提案
2. 确认技术方案
3. 开始实施（参考 tasks.md）
