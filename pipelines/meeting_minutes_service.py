"""Reusable meeting minutes generation utilities."""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from dashscope import Generation

from api.audio_models import MeetingMinutes

logger = logging.getLogger(__name__)


class MeetingMinutesService:
    """Generate structured meeting minutes from transcription text."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_path: Optional[Path] = None,
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is required for meeting minutes generation")

        self.model_name = model_name or os.getenv("MEETING_MINUTES_MODEL", "qwen-plus-latest")
        prompt_file = prompt_path or (Path(__file__).parent / "prompts" / "meeting_minutes.txt")
        self.minutes_prompt_template = prompt_file.read_text(encoding="utf-8")
        logger.info("MeetingMinutesService initialized with model: %s", self.model_name)

    def generate_minutes(self, transcription: str) -> MeetingMinutes:
        """Generate structured meeting minutes via LLM."""
        if not transcription:
            raise ValueError("Transcription text is required to generate meeting minutes")

        prompt = self.minutes_prompt_template.format(transcription_text=transcription)
        try:
            response = Generation.call(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                temperature=0.3,
                result_format="message",
            )
        except Exception as exc:
            logger.error("LLM meeting minutes call failed: %s", exc)
            raise RuntimeError("LLM generation failed") from exc

        if response.status_code != 200:
            logger.error("LLM API returned non-200: code=%s msg=%s", response.status_code, response.message)
            raise RuntimeError(f"LLM API error: {response.message}")

        content = response.output.choices[0].message.content
        minutes = self._parse_meeting_minutes(content)
        return minutes

    def save_as_markdown(
        self,
        meeting_minutes: MeetingMinutes,
        output_path: Path,
        transcript: Optional[str] = None,
    ) -> Path:
        """Persist meeting minutes (optionally transcript) as Markdown."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        markdown_lines = [
            f"# {meeting_minutes.title}",
            "",
            "## 主要内容",
            "",
            meeting_minutes.content,
            "",
        ]

        if meeting_minutes.key_quotes:
            markdown_lines.extend(["## 关键引述", ""])
            for quote in meeting_minutes.key_quotes:
                if quote:
                    markdown_lines.append(f"> {quote}")
                    markdown_lines.append("")

        if meeting_minutes.keywords:
            markdown_lines.extend(["## 关键词", ""])
            keywords_formatted = ", ".join(f"`{kw}`" for kw in meeting_minutes.keywords)
            markdown_lines.append(keywords_formatted)
            markdown_lines.append("")

        if transcript:
            markdown_lines.extend(["## 全文转写", "", transcript, ""])

        output_path.write_text("\n".join(markdown_lines), encoding="utf-8")
        return output_path

    def _parse_meeting_minutes(self, content: str) -> MeetingMinutes:
        """Parse LLM output into structured MeetingMinutes object."""
        import re

        title_match = re.search(r"【标题】\s*\n*(.*?)(?:\n|$)", content)
        title = title_match.group(1).strip() if title_match else "会议纪要"

        content_match = re.search(r"【主要内容】(.*?)【关键引述】", content, re.DOTALL)
        main_content = content_match.group(1).strip() if content_match else content

        quotes_match = re.search(r"【关键引述】(.*?)【关键词】", content, re.DOTALL)
        quotes_text = quotes_match.group(1).strip() if quotes_match else ""
        key_quotes = [
            line.strip().strip("-").strip()
            for line in quotes_text.split("\n")
            if line.strip() and line.strip() != "-"
        ]

        keywords = re.findall(r"<KEYWORD>(.*?)</KEYWORD>", content)

        return MeetingMinutes(
            title=title,
            content=main_content,
            key_quotes=key_quotes[:5] if key_quotes else [],
            keywords=keywords[:8] if keywords else [],
            generated_at=datetime.utcnow(),
        )
