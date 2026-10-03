from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator

from openai import AsyncOpenAI

from ..config import Settings


@dataclass(frozen=True, slots=True)
class ChapterInput:
    chapter_title: str
    node_title: str
    time_range: str
    location: str
    research_summary: str
    visible_context: str
    chapter_guidance: str
    life_number: int
    inherited_memories: tuple[dict, ...]
    committed_text: str = ""


class ModelSelector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def choose(self, estimated_input_tokens: int, estimated_output_tokens: int) -> str:
        candidates = [self.settings.ai_primary_model, self.settings.ai_alternate_model]
        candidates = [item for item in dict.fromkeys(candidates) if item]
        priced = [item for item in candidates if item in self.settings.ai_model_prices_json]
        if priced:
            def cost(model: str) -> float:
                price = self.settings.ai_model_prices_json[model]
                return (
                    float(price.get("input_per_1m", 0)) * estimated_input_tokens / 1_000_000
                    + float(price.get("output_per_1m", 0)) * estimated_output_tokens / 1_000_000
                )
            return min(priced, key=cost)
        return self.settings.ai_primary_model or "gpt-5.6-luna"

    async def verify(self) -> list[str]:
        if not self.settings.ai_api_key:
            raise RuntimeError("AI_API_KEY is missing")
        client = AsyncOpenAI(
            api_key=self.settings.ai_api_key,
            base_url=self.settings.ai_base_url,
            timeout=self.settings.ai_timeout_seconds,
        )
        response = await client.models.list()
        available = {item.id for item in response.data}
        targets = {self.settings.ai_primary_model, self.settings.ai_alternate_model}
        missing = sorted(item for item in targets if item and item not in available)
        if missing:
            raise RuntimeError(f"Configured models are unavailable: {', '.join(missing)}")
        return sorted(available & targets)


class ChapterWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.selector = ModelSelector(settings)

    async def stream_chapter(self, chapter: ChapterInput) -> AsyncIterator[str]:
        if not self.settings.ai_api_key:
            yield self._fallback_text(chapter)
            return
        model = self.selector.choose(estimated_input_tokens=1600, estimated_output_tokens=self.settings.ai_max_output_tokens)
        client = AsyncOpenAI(
            api_key=self.settings.ai_api_key,
            base_url=self.settings.ai_base_url,
            timeout=self.settings.ai_timeout_seconds,
        )
        memories = json.dumps(list(chapter.inherited_memories), ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是《我的模拟首富路》的直播小说作者。只写虚构叙事，不新增骰子、不改变真实节点顺序、"
                    "不把研究摘要扩写成未经证实的现实事实。输出简体中文小说正文，不要标题，不要 markdown。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"章节：{chapter.chapter_title}\n世数：{chapter.life_number}\n"
                    f"时间：{chapter.time_range}\n地点：{chapter.location}\n"
                    f"真实节点：{chapter.node_title}\n研究摘要：{chapter.research_summary}\n"
                    f"当时可知：{chapter.visible_context}\n文学边界：{chapter.chapter_guidance}\n"
                    f"跨世记忆：{memories}\n已提交正文：{chapter.committed_text}\n"
                    f"请继续写约 {self.settings.chapter_target_words} 字，结尾停在节点判定前。"
                ),
            },
        ]
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=self.settings.ai_max_output_tokens,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    @staticmethod
    def _fallback_text(chapter: ChapterInput) -> str:
        return (
            f"{chapter.chapter_title}\n\n"
            f"第{chapter.life_number}世，故事来到{chapter.time_range}的{chapter.location}。"
            f"关于“{chapter.node_title}”，公开资料只确认了一个现实锚点：{chapter.research_summary}"
            "其余选择仍属于这部平行世界小说。风声从屏幕另一端传来，下一次判定正在逼近。"
        )

