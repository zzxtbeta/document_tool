"""
表格处理 Pipeline - 从 MinerU 输出的 content_list.json 中提取表格信息并生成知识图谱

核心特点：
1. ✅ 直接处理已识别的 HTML 表格（无需 VL 模型）
2. ✅ 两阶段实体提取：LLM 提取 + Ontology 对齐
3. ✅ 两个独立输出文件：_table_raw.json + _table_kg_aligned.json
4. ✅ 格式统一：与 text/image pipeline 输出一致
"""
import os
import sys
import json
import re
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from tqdm import tqdm
from langchain_openai import ChatOpenAI
from bs4 import BeautifulSoup

# 处理相对导入问题
if __name__ == "__main__":
    # 直接运行时添加父目录到路径
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from table_models import TableDescription, TableRawData, TableRawOutput, TableEntity, TableRelation, TableKGOutput, TablePipelineConfig
else:
    # 作为模块导入时使用相对导入
    from .table_models import TableDescription, TableRawData, TableRawOutput, TableEntity, TableRelation, TableKGOutput, TablePipelineConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TableContentParser:
    """HTML 表格解析器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def parse_html_table(self, html: str) -> Dict:
        """解析 HTML 表格"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return {"rows": [], "structure": {}}
            
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cells.append({
                        "text": cell.get_text(strip=True),
                        "rowspan": int(cell.get('rowspan', 1)),
                        "colspan": int(cell.get('colspan', 1))
                    })
                rows.append(cells)
            
            structure = {
                "rows": len(rows),
                "cols": max(len(row) for row in rows) if rows else 0,
                "header_row": len(rows) > 0
            }
            
            return {"rows": rows, "structure": structure}
            
        except Exception as e:
            self.logger.warning(f"表格解析失败: {e}")
            return {"rows": [], "structure": {}}
    
    def clean_table_content(self, html: str) -> str:
        """清理 HTML 标签，提取纯文本"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            return html


class TableDescriptor:
    """表格描述生成器"""
    
    def __init__(
        self,
        config: TablePipelineConfig,
        logger: logging.Logger
    ):
        self.config = config
        self.logger = logger
        
        # 初始化 LLM 客户端
        self.llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_file = Path(__file__).parent / "prompts" / "table_description.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        else:
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
    
    def generate_description(
        self,
        table_body: str,
        table_caption: List[str],
        table_footnote: List[str]
    ) -> Tuple[str, Dict]:
        """生成表格描述"""
        try:
            # 渲染提示词
            prompt = self.prompt_template.format(
                table_caption=", ".join(table_caption) if table_caption else "无",
                table_body=table_body[:2000],  # 限制长度
                table_footnote=", ".join(table_footnote) if table_footnote else "无"
            )
            
            # 调用 LLM
            response = self.llm.invoke(prompt)
            response_text = response.content
            
            # 鲁棒 JSON 解析
            parsed_data = self._robust_json_parse(response_text)
            
            description = parsed_data.get("description", "")
            entity_info = {
                "entity_name": parsed_data.get("entity_name", "未知表格"),
                "type": parsed_data.get("type", "表格"),
                "description": description
            }
            
            return description, entity_info
            
        except Exception as e:
            self.logger.error(f"表格描述生成失败: {e}")
            # 降级处理
            fallback_description = f"表格内容: {table_body[:100]}..."
            fallback_entity = {
                "entity_name": "未知表格",
                "type": "表格",
                "description": fallback_description
            }
            return fallback_description, fallback_entity
    
    def _robust_json_parse(self, response: str) -> Dict:
        """鲁棒 JSON 解析"""
        # 策略1: 直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 策略2: 去除 Markdown 代码块
        try:
            cleaned = re.sub(r'```(?:json)?\s*', '', response)
            cleaned = cleaned.replace('```', '')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 策略3: 提取第一个 JSON 对象
        try:
            start = response.find('{')
            if start != -1:
                brace_count = 0
                for i in range(start, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return json.loads(response[start:i+1])
        except json.JSONDecodeError:
            pass
        
        # 降级：返回默认值
        self.logger.error(f"JSON 解析失败，响应前500字符: {response[:500]}")
        return {
            "entity_name": "未知表格",
            "type": "表格",
            "description": response[:100]
        }


class TableEntityExtractor:
    """表格实体提取器"""
    
    def __init__(
        self,
        config: TablePipelineConfig,
        logger: logging.Logger
    ):
        self.config = config
        self.logger = logger
        
        # 初始化 LLM 客户端
        self.llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        
        # 加载 OntologyAligner（与 text/image pipeline 共享）
        try:
            if __name__ == "__main__":
                from text_pipeline import OntologyAligner
            else:
                from .text_pipeline import OntologyAligner
            self.aligner = OntologyAligner()
            self.logger.info("成功加载 OntologyAligner")
        except Exception as e:
            self.logger.warning(f"无法加载 OntologyAligner: {e}")
            self.aligner = None
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_file = Path(__file__).parent / "prompts" / "table_entity_extraction.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        else:
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
    
    def extract_entities_from_description(
        self,
        description: str,
        table_info: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """从表格描述中提取实体和关系"""
        try:
            # 渲染提示词
            prompt = self.prompt_template.format(description=description)
            
            # 调用 LLM
            response = self.llm.invoke(prompt)
            
            # 解析响应
            try:
                response_data = self._robust_json_parse(response.content)
            except Exception as parse_error:
                self.logger.error(f"JSON 解析失败: {parse_error}")
                self.logger.debug(f"原始响应内容: {response.content[:1000]}")
                return [], []
            
            entities = response_data.get("entities", [])
            relations = response_data.get("relations", [])
            
            # 添加 source_table 和 page_idx
            for entity in entities:
                entity["source_table"] = table_info.get("img_path", "")
                entity["page_idx"] = table_info.get("page_idx", 0)
            
            return entities, relations
            
        except Exception as e:
            self.logger.error(f"实体提取失败: {e}")
            return [], []
    
    def align_entities(self, raw_entities: List[Dict]) -> Dict[str, Dict]:
        """对齐实体到核心本体类型"""
        if not self.aligner:
            self.logger.warning("OntologyAligner 未加载，跳过对齐")
            return {entity["name"]: entity for entity in raw_entities}
        
        try:
            # 导入 Entity 类
            if __name__ == "__main__":
                from text_pipeline import Entity, EntityAttribute
            else:
                from .text_pipeline import Entity, EntityAttribute
            
            # 转换为 Entity 对象字典（⭐ 关键：必须是字典，不是列表）
            entities_dict = {}
            for raw_entity in raw_entities:
                entity_attrs = [
                    EntityAttribute(name=attr["name"], value=attr["value"])
                    for attr in raw_entity.get("attributes", [])
                ]
                
                entity = Entity(
                    name=raw_entity["name"],
                    type=raw_entity["type"],
                    description=raw_entity.get("description", ""),
                    attributes=entity_attrs
                )
                entities_dict[entity.name] = entity
            
            # OntologyAligner.align_entities 期望 Dict[str, Entity]
            aligned_entities = self.aligner.align_entities(entities_dict)
            
            # 转换为 Dict 格式，补充 table 特有字段
            aligned_dict = {}
            for name, aligned_entity in aligned_entities.items():
                entity_dict = aligned_entity.model_dump(exclude_none=True)
                
                # 补充 table 特有字段（从原始实体）
                orig = next((e for e in raw_entities if e["name"] == name), None)
                if orig:
                    entity_dict["source_table"] = orig.get("source_table", "")
                    entity_dict["page_idx"] = orig.get("page_idx", 0)
                
                aligned_dict[name] = entity_dict
            
            return aligned_dict
            
        except Exception as e:
            self.logger.error(f"实体对齐失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 降级：返回原始实体
            return {entity["name"]: entity for entity in raw_entities}
    
    def _robust_json_parse(self, response: str) -> Dict:
        """鲁棒 JSON 解析"""
        # 策略1: 直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 策略2: 去除 Markdown 代码块标记
        try:
            cleaned = re.sub(r'```(?:json)?\s*', '', response)
            cleaned = cleaned.replace('```', '')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 策略3: 提取第一个完整的 JSON 对象
        try:
            start = response.find('{')
            if start != -1:
                brace_count = 0
                for i in range(start, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start:i+1]
                            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 所有策略失败
        raise json.JSONDecodeError(
            f"无法解析 JSON，前500字符: {response[:500]}",
            response, 0
        )


class TableKnowledgeGraphPipeline:
    """表格知识图谱提取主流程"""
    
    def __init__(self, config: TablePipelineConfig):
        self.config = config
        self.logger = logger
        
        # 初始化组件
        self.parser = TableContentParser(self.logger)
        self.descriptor = TableDescriptor(config, self.logger)
        self.extractor = TableEntityExtractor(config, self.logger)
    
    def load_content_list(self, input_path: str) -> List[Dict]:
        """加载 content_list.json"""
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            content_list = json.load(f)
        
        self.logger.info(f"加载文件: {input_path}")
        self.logger.info(f"总条目数: {len(content_list)}")
        
        return content_list
    
    def collect_and_filter_tables(self, content_list: List[Dict]) -> Tuple[List[Dict], Dict]:
        """收集并过滤表格"""
        # 收集所有 type="table" 的条目
        all_tables = [item for item in content_list if item.get("type") == "table"]
        
        # 过滤空表格
        valid_tables = []
        filtered_count = 0
        
        for table in all_tables:
            table_body = table.get("table_body", "")
            if len(table_body) < self.config.min_table_length:
                filtered_count += 1
                continue
            valid_tables.append(table)
        
        stats = {
            "total_tables": len(all_tables),
            "filtered_tables": filtered_count,
            "valid_tables": len(valid_tables)
        }
        
        self.logger.info("=" * 60)
        self.logger.info(f"【表格收集】总数：{stats['total_tables']} | "
                        f"有效：{stats['valid_tables']} | "
                        f"过滤：{stats['filtered_tables']}")
        self.logger.info("=" * 60)
        
        return valid_tables, stats
    
    def process_single_table(self, table: Dict, table_idx: int, total_tables: int) -> Tuple[Dict, List, List]:
        """处理单个表格"""
        img_path = table.get("img_path", "unknown")
        page_idx = table.get("page_idx", 0)
        
        # 日志：处理开始
        if self.config.verbose:
            self.logger.info(f"[{table_idx+1}/{total_tables}] 处理表格: {img_path} (页码: {page_idx})")
        
        try:
            # 1. 解析表格
            table_data = self.parser.parse_html_table(table.get("table_body", ""))
            
            # 2. 生成描述
            description, entity_info = self.descriptor.generate_description(
                table.get("table_body", ""),
                table.get("table_caption", []),
                table.get("table_footnote", [])
            )
            
            # 3. 提取实体
            raw_entities, raw_relations = self.extractor.extract_entities_from_description(
                description,
                table
            )
            
            # 日志：提取结果
            if self.config.verbose:
                self.logger.info(f"  ✓ {entity_info.get('entity_name', '未知')} | "
                               f"实体: {len(raw_entities)} | 关系: {len(raw_relations)}")
            
            # 4. 构建 raw_data
            raw_data = {
                "img_path": img_path,
                "page_idx": page_idx,
                "entity_name": entity_info.get("entity_name", ""),
                "type": entity_info.get("type", ""),
                "description": description,
                "table_caption": table.get("table_caption", []),
                "table_body": table.get("table_body", ""),
                "table_structure": table_data.get("structure", {})
            }
            
            return raw_data, raw_entities, raw_relations
            
        except Exception as e:
            self.logger.error(f"  ✗ 表格处理失败 ({img_path}): {e}")
            return {}, [], []
    
    def run(self, input_path: str):
        """执行完整的表格处理流程"""
        start_time = time.time()
        
        self.logger.info("=" * 60)
        self.logger.info("开始表格知识图谱提取")
        self.logger.info("=" * 60)
        
        # 1. 加载数据
        content_list = self.load_content_list(input_path)
        
        # 2. 收集与过滤表格
        valid_tables, filter_stats = self.collect_and_filter_tables(content_list)
        
        if not valid_tables:
            self.logger.warning("没有有效的表格，退出处理")
            return
        
        # 3. 处理每个表格
        self.logger.info(f"开始处理 {len(valid_tables)} 个有效表格...")
        self.logger.info("=" * 60)
        
        all_raw_data = []
        all_raw_entities = []
        all_raw_relations = []
        
        total_tables = len(valid_tables)
        
        # 使用 tqdm 进度条（非 verbose 模式）或详细日志（verbose 模式）
        iterator = enumerate(valid_tables)
        if not self.config.verbose:
            iterator = tqdm(
                enumerate(valid_tables), 
                total=total_tables,
                desc="处理表格",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )
        
        for idx, table in iterator:
            raw_data, raw_entities, raw_relations = self.process_single_table(
                table, idx, total_tables
            )
            if raw_data:
                all_raw_data.append(raw_data)
                all_raw_entities.extend(raw_entities)
                all_raw_relations.extend(raw_relations)
        
        self.logger.info("=" * 60)
        self.logger.info(f"✓ 处理完成 | 实体: {len(all_raw_entities)} | 关系: {len(all_raw_relations)}")
        
        # 4. 实体对齐
        self.logger.info("=" * 60)
        self.logger.info(f"开始实体对齐 ({len(all_raw_entities)} 个原始实体)...")
        aligned_entities = self.extractor.align_entities(all_raw_entities)
        
        # 统计对齐后的实体类型分布
        aligned_type_counts = {}
        for entity in aligned_entities.values():
            core_type = entity.get("core_type", "Other")
            aligned_type_counts[core_type] = aligned_type_counts.get(core_type, 0) + 1
        
        self.logger.info(f"✓ 对齐完成 | 对齐后实体: {len(aligned_entities)}")
        if aligned_type_counts:
            type_summary = ", ".join([f"{k}:{v}" for k, v in sorted(aligned_type_counts.items())])
            self.logger.info(f"  类型分布: {type_summary}")
        
        # 5. 输出文件
        self.logger.info("=" * 60)
        output_files = self.save_outputs(
            input_path,
            all_raw_data,
            all_raw_entities,
            all_raw_relations,
            aligned_entities,
            filter_stats
        )
        
        elapsed_time = time.time() - start_time
        self.logger.info("=" * 60)
        self.logger.info(f"✓ 表格知识图谱提取完成")
        self.logger.info(f"  耗时: {elapsed_time:.2f}秒")
        self.logger.info(f"  输出文件:")
        self.logger.info(f"    - Raw: {output_files['raw']}")
        self.logger.info(f"    - Aligned: {output_files['aligned']}")
        self.logger.info("=" * 60)
    
    def save_outputs(
        self,
        input_path: str,
        all_raw_data: List[Dict],
        all_raw_entities: List[Dict],
        all_raw_relations: List[Dict],
        aligned_entities: Dict[str, Dict],
        filter_stats: Dict
    ) -> Dict[str, str]:
        """保存输出文件，返回文件路径"""
        input_file = Path(input_path)
        output_dir = Path(self.config.output_dir) if self.config.output_dir else input_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        base_name = input_file.stem.replace("_content_list", "")
        raw_file = output_dir / f"{base_name}_table_raw.json"
        aligned_file = output_dir / f"{base_name}_table_kg_aligned.json"
        
        # 转换 entities 为 Dict 格式
        entities_dict = {
            entity["name"]: entity
            for entity in all_raw_entities
        }
        
        # 统计信息
        entity_types = list(set(e["type"] for e in all_raw_entities))
        relation_types = list(set(r["type"] for r in all_raw_relations))
        
        # 文件1: *_table_raw.json
        raw_output = {
            "metadata": {
                # 通用字段
                "source_file": str(input_path),
                "pipeline_type": "table",
                "pipeline_version": "2.0",
                "build_time": datetime.now().isoformat(),
                
                # 统计信息
                "total_entities": len(all_raw_entities),
                "total_relations": len(all_raw_relations),
                "entity_types": entity_types,
                "relation_types": relation_types,
                
                # Table pipeline 特有字段
                "total_tables": filter_stats["total_tables"],
                "filtered_tables": filter_stats["filtered_tables"],
                "valid_tables": filter_stats["valid_tables"],
                "min_table_length": self.config.min_table_length
            },
            "tables": all_raw_data,
            "entities": entities_dict,
            "relations": all_raw_relations
        }
        
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_output, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"✓ 保存原始数据: {raw_file.name}")
        
        # 文件2: *_table_kg_aligned.json
        aligned_entity_types = list(set(
            e.get("core_type", e.get("type", "")) 
            for e in aligned_entities.values()
        ))
        
        aligned_output = {
            "metadata": {
                # 通用字段
                "source_file": str(input_path),
                "pipeline_type": "table",
                "data_source": "table_pipeline",
                "ontology_version": "v1.2.1",
                "build_time": datetime.now().isoformat(),
                
                # 统计信息
                "total_aligned_entities": len(aligned_entities),
                "aligned_entity_types": aligned_entity_types,
                
                # 核心类型定义
                "core_entity_types": ["Company", "Person", "Technology", "Product", "TagConcept", "Event", "Signal", "Other"]
            },
            "aligned_entities": aligned_entities,
            "aligned_relations": all_raw_relations  # TODO: 关系也需要对齐
        }
        
        with open(aligned_file, 'w', encoding='utf-8') as f:
            json.dump(aligned_output, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"✓ 保存对齐数据: {aligned_file.name}")
        
        # 返回文件名（不含路径，便于日志输出）
        return {
            "raw": raw_file.name,
            "aligned": aligned_file.name
        }


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="表格知识图谱提取 Pipeline")
    parser.add_argument("input", help="输入文件路径 (content_list.json)")
    parser.add_argument("--output-dir", help="输出目录（默认与输入文件同目录）")
    parser.add_argument("--model", default="qwen-plus-latest", help="LLM 模型名称")
    parser.add_argument("--min-length", type=int, default=50, help="最小表格长度")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    
    args = parser.parse_args()
    
    # 创建配置
    config = TablePipelineConfig(
        model_name=args.model,
        min_table_length=args.min_length,
        verbose=args.verbose,
        output_dir=args.output_dir
    )
    
    # 创建 Pipeline
    pipeline = TableKnowledgeGraphPipeline(config)
    
    # 运行
    pipeline.run(args.input)


if __name__ == "__main__":
    main()
