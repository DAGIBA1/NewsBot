"""Telegram 推播模組 — 將格式化晨報發送至各分類 Channel。"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone, timedelta

import requests

from config import CATEGORY_CHANNEL_ENV, TELEGRAM_MESSAGE_LIMIT
from reddit_scraper import CategoryPosts

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TW_TZ = timezone(timedelta(hours=8))


def _get_bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _get_channel_id(category: str) -> str:
    env_key = CATEGORY_CHANNEL_ENV.get(category, "")
    return os.getenv(env_key, "")


def format_category_message(cat: CategoryPosts) -> str:
    """將單一分類的貼文格式化為 Telegram 訊息。"""
    today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    lines = [f"{cat.emoji} 【{cat.category}】每日情報 ({today})", ""]

    for post in cat.posts:
        lines.append(f"\U0001f53c [{post.score}] {post.title}")
        if hasattr(post, "summary") and post.summary:
            lines.append(post.summary)
        lines.append(f"\U0001f517 {post.permalink}")
        lines.append("")

    if not cat.posts:
        lines.append("今日無新貼文。")

    return "\n".join(lines).strip()


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """將超過長度限制的訊息按換行拆分成多段。"""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line[:limit]  # 單行超長時截斷
        else:
            current = candidate
    if current:
        chunks.append(current)

    return chunks


def send_to_channel(
    bot_token: str,
    channel_id: str,
    message: str,
    max_retries: int = 2,
) -> bool:
    """發送訊息到指定 Telegram Channel，含簡易重試邏輯。"""
    url = TELEGRAM_API_URL.format(token=bot_token)

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                url,
                json={"chat_id": channel_id, "text": message},
                timeout=15,
            )
            if resp.status_code == 200:
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                logger.warning("Rate limited, waiting %d seconds", retry_after)
                time.sleep(retry_after)
                continue
            logger.error("Telegram API 回傳 %d: %s", resp.status_code, resp.text)
        except requests.RequestException:
            logger.exception("發送訊息至 %s 失敗 (attempt %d)", channel_id, attempt + 1)

    return False


def dispatch_reports(categories: list[CategoryPosts]) -> None:
    """將所有分類的晨報發送到對應的 Telegram Channel。"""
    bot_token = _get_bot_token()
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN 未設定")
        return

    for cat in categories:
        channel_id = _get_channel_id(cat.category)
        if not channel_id:
            logger.warning("分類 '%s' 無對應的 Channel ID，跳過", cat.category)
            continue

        message = format_category_message(cat)
        chunks = split_message(message)

        for chunk in chunks:
            success = send_to_channel(bot_token, channel_id, chunk)
            if not success:
                logger.error("推播至 %s (%s) 失敗", cat.category, channel_id)
