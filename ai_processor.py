"""AI 處理模組 — 使用 Google Gemini 進行翻譯與摘要。"""

from __future__ import annotations

import logging
import os

from google import genai
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一個專業的國際新聞編譯與金融分析師。請將以下英文 Reddit 貼文的標題與內文，翻譯並總結為流暢的「台灣繁體中文」。
請嚴格遵守以下輸出格式：
1. 第一行：[繁體中文翻譯標題]
2. 接下來用 3 個條列式重點 (Bullet points)，總結這篇文章的核心價值、結論或市場情緒。
如果原文很短無內文，請僅憑標題推測其重點。不要輸出任何多餘的問候語。"""

FALLBACK_MESSAGE = "⚠️ AI 摘要生成失敗，請直接點擊原文連結閱讀。"


def _create_client() -> genai.Client:
    """建立 Gemini API 客戶端。"""
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def summarize_post(
    title: str,
    selftext: str,
    client: genai.Client | None = None,
) -> str:
    """將英文貼文翻譯摘要為繁中。

    回傳格式：
        [繁體中文標題]
        - 重點 1
        - 重點 2
        - 重點 3

    若 API 呼叫失敗，回傳預設錯誤字串。
    """
    if client is None:
        client = _create_client()

    user_content = f"標題：{title}"
    if selftext.strip():
        user_content += f"\n\n內文：{selftext[:3000]}"  # 截斷過長內文

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                http_options={"timeout": 30_000},
            ),
        )

        if response.text:
            return response.text.strip()

        logger.warning("Gemini 回傳空內容")
        return FALLBACK_MESSAGE

    except Exception:
        logger.exception("Gemini API 呼叫失敗")
        return FALLBACK_MESSAGE
