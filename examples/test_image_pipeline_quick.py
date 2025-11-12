"""
快速测试图片 Pipeline
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines import ImageKnowledgeGraphPipeline, ImagePipelineConfig


def test_import():
    """测试导入"""
    print("✓ 模块导入成功")
    print(f"  - ImageKnowledgeGraphPipeline: {ImageKnowledgeGraphPipeline}")
    print(f"  - ImagePipelineConfig: {ImagePipelineConfig}")


def test_config():
    """测试配置"""
    config = ImagePipelineConfig(
        ocr_engine="auto",
        res_preset="s",
        min_text_len=10,
        multimodal_model="qwen3-vl-flash"
    )
    print("✓ 配置创建成功")
    print(f"  - OCR Engine: {config.ocr_engine}")
    print(f"  - Resolution Preset: {config.res_preset}")
    print(f"  - Multimodal Model: {config.multimodal_model}")


def test_pipeline_init():
    """测试 Pipeline 初始化"""
    config = ImagePipelineConfig()
    
    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠ 警告: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("  请在 .env 文件中配置或通过以下命令设置:")
        print("  export DASHSCOPE_API_KEY=your_api_key")
        return False
    
    try:
        pipeline = ImageKnowledgeGraphPipeline(config)
        print("✓ Pipeline 初始化成功")
        print(f"  - Context Extractor: {pipeline.context_extractor}")
        print(f"  - Multimodal Descriptor: {pipeline.descriptor}")
        print(f"  - Entity Extractor: {pipeline.entity_extractor}")
        return True
    except Exception as e:
        print(f"✗ Pipeline 初始化失败: {e}")
        return False


def test_file_exists():
    """测试示例文件是否存在"""
    test_file = Path("parsed/象量科技项目介绍20250825/auto/象量科技项目介绍20250825_content_list.json")
    if test_file.exists():
        print(f"✓ 测试文件存在: {test_file}")
        return True
    else:
        print(f"⚠ 测试文件不存在: {test_file}")
        print("  请确保已运行过 MinerU 解析")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("图片 Pipeline 快速测试")
    print("=" * 60)
    
    print("\n【测试 1】模块导入")
    test_import()
    
    print("\n【测试 2】配置创建")
    test_config()
    
    print("\n【测试 3】Pipeline 初始化")
    success = test_pipeline_init()
    
    print("\n【测试 4】示例文件检查")
    file_exists = test_file_exists()
    
    print("\n" + "=" * 60)
    if success and file_exists:
        print("✓ 所有测试通过！可以开始使用图片 Pipeline")
        print("\n运行示例:")
        print('  python pipelines/image_pipeline.py "parsed/象量科技项目介绍20250825/auto/象量科技项目介绍20250825_content_list.json"')
    else:
        print("⚠ 部分测试未通过，请检查配置")
    print("=" * 60)


if __name__ == "__main__":
    main()
