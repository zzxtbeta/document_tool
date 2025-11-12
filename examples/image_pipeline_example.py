"""
图片处理 Pipeline 使用示例
"""
from pathlib import Path
from pipelines import ImageKnowledgeGraphPipeline, ImagePipelineConfig


def example_basic():
    """基础用法示例"""
    # 配置
    config = ImagePipelineConfig(
        ocr_engine="auto",  # 自动选择 OCR 引擎
        res_preset="s",  # 小图过滤（28万像素）
        min_text_len=10,  # 最小文本长度
        context_window=2,  # 上下文窗口
        multimodal_model="qwen3-vl-flash"  # 多模态模型
    )
    
    # 创建 Pipeline
    pipeline = ImageKnowledgeGraphPipeline(config)
    
    # 运行处理
    input_file = "parsed/象量科技项目介绍20250825/auto/象量科技项目介绍20250825_content_list.json"
    pipeline.run(input_file)


def example_custom_config():
    """自定义配置示例"""
    config = ImagePipelineConfig(
        ocr_engine="easyocr",  # 指定 EasyOCR
        res_preset="m",  # 中等图过滤（60万像素）
        min_text_len=15,
        context_window=3,  # 更大的上下文窗口
        multimodal_model="qwen3-vl-plus",  # 使用更强的模型
        temperature=0.0,  # 更确定性的输出
        output_dir="output/images"  # 自定义输出目录
    )
    
    pipeline = ImageKnowledgeGraphPipeline(config)
    pipeline.run(
        input_path="path/to/content_list.json",
        output_dir="path/to/output"
    )


def example_no_filter():
    """不过滤图片示例"""
    config = ImagePipelineConfig(
        res_preset="off",  # 关闭分辨率过滤
        min_text_len=0,  # 关闭文本长度过滤
        ocr_engine="none"  # 不使用 OCR
    )
    
    pipeline = ImageKnowledgeGraphPipeline(config)
    pipeline.run("path/to/content_list.json")


if __name__ == "__main__":
    # 运行基础示例
    example_basic()
