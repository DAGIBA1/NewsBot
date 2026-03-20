"""AI 處理模組 — 使用 Google Gemini 進行翻譯與摘要。"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING

from google import genai
from google.genai import errors as genai_errors
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL

if TYPE_CHECKING:
    from reddit_scraper import RedditPost

logger = logging.getLogger(__name__)

BATCH_SYSTEM_PROMPT = """\
你是一個專業的國際新聞編譯與金融分析師。
我會提供多篇英文 Reddit 貼文（以 === POST 1 ===, === POST 2 === ... 分隔）。
請依序將每篇的標題與內文翻譯並總結為流暢的「台灣繁體中文」。

請嚴格遵守以下輸出格式，每篇之間用分隔線區分：
=== POST 1 ===
[繁體中文翻譯標題]
- 重點 1
- 重點 2
- 重點 3

=== POST 2 ===
[繁體中文翻譯標題]
- 重點 1
- 重點 2
- 重點 3

規則：
- 每篇固定 3 個條列式重點，總結核心價值、結論或市場情緒。
- 如果原文很短無內文，請僅憑標題推測其重點。
- 不要輸出任何多餘的問候語。
- 分隔線格式必須嚴格遵守：=== POST N ==="""

FALLBACK_MESSAGE = "⚠️ AI 摘要生成失敗，請直接點擊原文連結閱讀。"

# Gemini 2.5 Flash 免費方案 RPM 限制為 5，間隔 13 秒確保不超額
_REQUEST_INTERVAL = 13
_last_request_time: float = 0


def _load_api_keys() -> list[str]:
    """從環境變數載入 API key 清單。

    支援兩種格式：
      - GEMINI_API_KEY=key1,key2,key3  (逗號分隔)
      - GEMINI_API_KEY=single_key
    """
    raw = os.getenv("GEMINI_API_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("未設定 GEMINI_API_KEY 環境變數")
    return keys


class _KeyPool:
    """管理多組 API key，額度用盡時自動輪換。"""

    def __init__(self) -> None:
        self.keys = _load_api_keys()
        self.index = 0
        self.client: genai.Client = self._make_client()
        logger.info("已載入 %d 組 Gemini API key", len(self.keys))

    def _make_client(self) -> genai.Client:
        return genai.Client(api_key=self.keys[self.index])

    def rotate(self) -> bool:
        """切換到下一把 key。回傳 False 表示所有 key 都已用過。"""
        self.index += 1
        if self.index >= len(self.keys):
            return False
        self.client = self._make_client()
        logger.warning(
            "切換至第 %d/%d 把 API key", self.index + 1, len(self.keys)
        )
        return True


_pool: _KeyPool | None = None


def _get_pool() -> _KeyPool:
    global _pool
    if _pool is None:
        _pool = _KeyPool()
    return _pool


def _build_batch_prompt(posts: list[RedditPost]) -> str:
    """將多篇貼文組合成單一 prompt。"""
    parts: list[str] = []
    for i, post in enumerate(posts, 1):
        section = f"=== POST {i} ===\n標題：{post.title}"
        if post.selftext.strip():
            section += f"\n\n內文：{post.selftext[:2000]}"
        parts.append(section)
    return "\n\n".join(parts)


def _parse_batch_response(text: str, count: int) -> list[str]:
    """解析批次回應，拆分為每篇的摘要。"""
    import re

    # 用 === POST N === 分割
    parts = re.split(r"===\s*POST\s*\d+\s*===", text)
    # 第一個分割結果通常是空字串（分隔符前面的內容）
    summaries = [p.strip() for p in parts if p.strip()]

    # 補齊不足的部分
    while len(summaries) < count:
        summaries.append(FALLBACK_MESSAGE)

    return summaries[:count]


def summarize_posts(posts: list[RedditPost]) -> list[str]:
    """批次翻譯摘要多篇貼文，回傳與 posts 等長的摘要清單。"""
    if not posts:
        return []

    pool = _get_pool()
    client = pool.client
    user_content = _build_batch_prompt(posts)

    while True:
        try:
            global _last_request_time
            elapsed = time.time() - _last_request_time
            if elapsed < _REQUEST_INTERVAL:
                time.sleep(_REQUEST_INTERVAL - elapsed)
            _last_request_time = time.time()

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_content,
                config=GenerateContentConfig(
                    system_instruction=BATCH_SYSTEM_PROMPT,
                    http_options={"timeout": 60_000},
                ),
            )

            if response.text:
                return _parse_batch_response(response.text, len(posts))

            logger.warning("Gemini 回傳空內容")
            return [FALLBACK_MESSAGE] * len(posts)

        except genai_errors.ClientError as exc:
            if exc.code == 429 and pool.rotate():
                client = pool.client
                _last_request_time = 0
                logger.info("額度用盡，使用新 key 重試...")
                continue
            logger.exception("Gemini API 呼叫失敗（所有 key 額度已耗盡）")
            return [FALLBACK_MESSAGE] * len(posts)

        except Exception:
            logger.exception("Gemini API 呼叫失敗")
            return [FALLBACK_MESSAGE] * len(posts)
