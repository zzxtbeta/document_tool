"""
Short Audio Processing Pipeline

Handles short audio transcription using DashScope ASR and meeting minutes generation.

Author: AI Assistant
Date: 2025-11-13
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from dashscope import MultiModalConversation, Generation
from pydantic import BaseModel

# Import models from api module
import sys
sys.path.append(str(Path(__file__).parent.parent))
from api.audio.shared_models import AudioMetadata, MeetingMinutes, ProcessingStats
from api.audio.short.models import AudioProcessingOutput

logger = logging.getLogger(__name__)


class AudioPipeline:
    """
    Audio processing pipeline for transcription and meeting minutes generation.
    
    Workflow:
    1. Validate audio file
    2. Transcribe audio using DashScope ASR
    3. Generate meeting minutes using LLM
    4. Return structured output
    """
    
    def __init__(self, api_key: Optional[str] = None, asr_model: Optional[str] = None):
        """
        Initialize AudioPipeline.
        
        Args:
            api_key: DashScope API key (defaults to DASHSCOPE_API_KEY env var)
            asr_model: ASR model name (defaults to AUDIO_ASR_MODEL env var or 'qwen3-asr-flash')
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is required")

        # Get ASR model from env or use default
        # read minimal env var name 'ASR_MODEL' per project config
        self.asr_model = asr_model or os.getenv("ASR_MODEL", "qwen3-asr-flash")

        # Load meeting minutes prompt
        prompt_path = Path(__file__).parent / "prompts" / "meeting_minutes.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.minutes_prompt_template = f.read()
        
        logger.info(f"AudioPipeline initialized with ASR model: {self.asr_model}")
    
    def validate_audio_file(self, file_path: str) -> AudioMetadata:
        """
        Validate audio file and extract metadata.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            AudioMetadata with file information
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Get file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        
        # Get file format
        file_format = path.suffix.lstrip('.').lower()
        supported_formats = ['m4a', 'mp3', 'wav', 'flac', 'opus', 'aac']
        
        if file_format not in supported_formats:
            raise ValueError(
                f"Unsupported audio format: {file_format}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )
        
        # For now, we can't easily get duration without additional libraries
        # So we estimate based on file size (rough estimate: 1MB ≈ 60 seconds for typical speech)
        estimated_duration = file_size_mb * 60
        
        metadata = AudioMetadata(
            duration_seconds=estimated_duration,
            format=file_format,
            file_size_mb=round(file_size_mb, 2),
            sample_rate=None,
            channels=None
        )
        
        logger.info(f"Audio file validated: {file_format}, {file_size_mb:.2f}MB")
        return metadata
    
    def transcribe_audio(
        self, 
        file_path: str, 
        enable_itn: bool = True,
        asr_context: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio using DashScope ASR API.
        
        Args:
            file_path: Path to audio file
            enable_itn: Enable inverse text normalization
            asr_context: Custom context for ASR (e.g., specialized terminology)
            language: Audio language code (e.g., 'zh', 'en')
            
        Returns:
            Transcribed text
            
        Raises:
            RuntimeError: If ASR API call fails
        """
        logger.info(f"Starting audio transcription: {file_path}")
        if asr_context:
            logger.info(f"Using ASR context: {asr_context[:100]}...")
        if language:
            logger.info(f"Using language: {language}")
        
        start_time = time.time()
        
        try:
            # Prepare messages for MultiModalConversation API
            messages = [
                {
                    "role": "system",
                    "content": [
                        {"text": asr_context or ""},  # Use provided context or empty string
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"audio": file_path},
                    ]
                }
            ]
            
            # Build ASR options
            asr_options = {
                "enable_itn": enable_itn
            }
            
            # Add language if specified
            if language:
                asr_options["language"] = language
            
            # Call DashScope ASR API using MultiModalConversation
            response = MultiModalConversation.call(
                api_key=self.api_key,
                model=self.asr_model,
                messages=messages,
                result_format='message',
                asr_options=asr_options
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"ASR API error: {response.message}")
            
            # Extract transcription text from response
            content = response.output.choices[0].message.content
            
            # Handle list of text segments
            if isinstance(content, list):
                text = ' '.join([item.get('text', '') for item in content if isinstance(item, dict)])
            elif isinstance(content, str):
                text = content
            else:
                text = str(content)
            
            if not text:
                raise RuntimeError("ASR returned empty transcription")
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.2f}s, text length: {len(text)}")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"ASR transcription failed: {str(e)}")
    
    def generate_meeting_minutes(self, transcription: str) -> MeetingMinutes:
        """
        Generate structured meeting minutes using LLM.
        
        Args:
            transcription: Full transcription text
            
        Returns:
            MeetingMinutes object with structured content
            
        Raises:
            RuntimeError: If LLM API call fails
        """
        logger.info("Generating meeting minutes with LLM")
        start_time = time.time()
        
        try:
            # Prepare prompt
            prompt = self.minutes_prompt_template.format(transcription_text=transcription)
            
            # Call LLM API
            response = Generation.call(
                model='qwen-plus-latest',
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                api_key=self.api_key,
                temperature=0.3,
                result_format='message'
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"LLM API error: {response.message}")
            
            # Extract generated text
            content = response.output.choices[0].message.content
            
            # Parse the structured output
            minutes = self._parse_meeting_minutes(content)
            
            elapsed = time.time() - start_time
            logger.info(f"Meeting minutes generated in {elapsed:.2f}s")
            
            return minutes
            
        except Exception as e:
            logger.error(f"Meeting minutes generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {str(e)}")
    
    def _parse_meeting_minutes(self, content: str) -> MeetingMinutes:
        """
        Parse LLM output into structured MeetingMinutes.
        
        Args:
            content: Raw LLM output
            
        Returns:
            MeetingMinutes object
        """
        # Extract title
        title_match = re.search(r'【标题】\s*\n*(.*?)(?:\n|$)', content)
        title = title_match.group(1).strip() if title_match else "会议纪要"
        
        # Extract main content (between 标题 and 关键引述)
        content_match = re.search(r'【主要内容】(.*?)【关键引述】', content, re.DOTALL)
        main_content = content_match.group(1).strip() if content_match else content
        
        # Extract key quotes
        quotes_match = re.search(r'【关键引述】(.*?)【关键词】', content, re.DOTALL)
        quotes_text = quotes_match.group(1).strip() if quotes_match else ""
        key_quotes = [
            line.strip().strip('-').strip()
            for line in quotes_text.split('\n')
            if line.strip() and line.strip() != '-'
        ]
        
        # Extract keywords (between <KEYWORD> tags)
        keywords = re.findall(r'<KEYWORD>(.*?)</KEYWORD>', content)
        
        return MeetingMinutes(
            title=title,
            content=main_content,
            key_quotes=key_quotes[:5] if key_quotes else [],  # Limit to 5
            keywords=keywords[:8] if keywords else [],  # Limit to 8
            generated_at=datetime.now()
        )
    
    def process(
        self,
        file_path: str,
        enable_itn: bool = True,
        asr_context: Optional[str] = None,
        language: Optional[str] = None
    ) -> AudioProcessingOutput:
        """
        Main processing pipeline: validate -> transcribe -> generate minutes.
        
        Args:
            file_path: Path to audio file
            enable_itn: Enable inverse text normalization for ASR
            asr_context: Custom context for ASR (specialized terminology)
            language: Audio language code (e.g., 'zh', 'en')
            
        Returns:
            AudioProcessingOutput with complete results
            
        Raises:
            Various exceptions from validation, transcription, or generation steps
        """
        logger.info(f"Starting audio processing pipeline: {file_path}")
        pipeline_start = time.time()
        
        # Step 1: Validate audio file
        audio_metadata = self.validate_audio_file(file_path)
        
        # Step 2: Transcribe audio
        transcription_start = time.time()
        transcription_text = self.transcribe_audio(
            file_path, 
            enable_itn=enable_itn,
            asr_context=asr_context,
            language=language
        )
        transcription_time = time.time() - transcription_start
        
        # Step 3: Generate meeting minutes
        llm_start = time.time()
        meeting_minutes = self.generate_meeting_minutes(transcription_text)
        llm_time = time.time() - llm_start
        
        # Calculate total time
        total_time = time.time() - pipeline_start
        
        processing_stats = ProcessingStats(
            total_time=round(total_time, 2),
            transcription_time=round(transcription_time, 2),
            llm_time=round(llm_time, 2)
        )
        
        result = AudioProcessingOutput(
            transcription_text=transcription_text,
            meeting_minutes=meeting_minutes,
            audio_metadata=audio_metadata,
            processing_stats=processing_stats
        )
        
        logger.info(f"Audio processing completed in {total_time:.2f}s")
        return result
    
    def save_as_markdown(
        self,
        meeting_minutes: MeetingMinutes,
        output_path: Path,
        transcript: Optional[str] = None
    ) -> Path:
        """
        Save meeting minutes as Markdown file.
        
        Args:
            meeting_minutes: MeetingMinutes object to save
            output_path: Path where the Markdown file will be saved
            transcript: Optional full transcript text to include
            
        Returns:
            Path to the saved Markdown file
        """
        # Build Markdown content
        markdown_lines = [
            f"# {meeting_minutes.title}",
            "",
            "## 主要内容",
            "",
            meeting_minutes.content,
            ""
        ]
        
        # Add key quotes if available
        if meeting_minutes.key_quotes:
            markdown_lines.extend([
                "## 关键引述",
                ""
            ])
            for quote in meeting_minutes.key_quotes:
                if quote:  # Skip empty quotes
                    markdown_lines.append(f"> {quote}")
                    markdown_lines.append("")
        
        # Add keywords if available
        if meeting_minutes.keywords:
            markdown_lines.extend([
                "## 关键词",
                ""
            ])
            keywords_formatted = ", ".join([f"`{kw}`" for kw in meeting_minutes.keywords])
            markdown_lines.append(keywords_formatted)
            markdown_lines.append("")
        
        # Add full transcript if provided
        if transcript:
            markdown_lines.extend([
                "## 完整转写",
                "",
                transcript,
                ""
            ])
        
        # Add footer with generation timestamp
        markdown_lines.extend([
            "---",
            f"*生成时间：{meeting_minutes.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        # Join lines and write to file
        markdown_content = "\n".join(markdown_lines)
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        output_path.write_text(markdown_content, encoding='utf-8')
        
        logger.info(f"Markdown file saved: {output_path}")
        return output_path
