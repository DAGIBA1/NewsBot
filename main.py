"""每日 Reddit 資訊監控與 AI 翻譯推播機器人 — 主程式進入點。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from config import SENT_POSTS_FILE
from reddit_scraper import fetch_all_categories
from ai_processor import summarize_posts
from notifier import dispatch_reports

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_sent_ids() -> set[str]:
    """從 JSON 檔載入已推播的 post ID。"""
    path = Path(SENT_POSTS_FILE)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data)
    except (json.JSONDecodeError, TypeError):
        logger.warning("sent_posts.json 格式錯誤，重新建立")
        return set()


def save_sent_ids(sent_ids: set[str]) -> None:
    """將已推播的 post ID 存回 JSON 檔。"""
    path = Path(SENT_POSTS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(sent_ids), ensure_ascii=False), encoding="utf-8")


def main() -> None:
    logger.info("===== NewsBot 開始執行 =====")

    # 1. 載入已推播的 post ID
    sent_ids = load_sent_ids()
    logger.info("已記錄 %d 篇已推播文章", len(sent_ids))

    # 2. 抓取所有分類的 Reddit 貼文
    categories = fetch_all_categories(sent_ids=sent_ids)
    total_posts = sum(len(cat.posts) for cat in categories)
    logger.info("抓取完成，共 %d 篇新貼文", total_posts)

    if total_posts == 0:
        logger.info("今日無新貼文，結束執行")
        return

    # 3. 透過 Gemini AI 批次翻譯摘要（每個分類 1 次 API 呼叫）
    new_ids: set[str] = set()
    for cat in categories:
        if not cat.posts:
            continue
        logger.info("批次摘要: %s（%d 篇）", cat.category, len(cat.posts))
        summaries = summarize_posts(cat.posts)
        for post, summary in zip(cat.posts, summaries):
            post.summary = summary  # type: ignore[attr-defined]
            new_ids.add(post.post_id)

    # 4. 推播至 Telegram
    dispatch_reports(categories)
    logger.info("推播完成")

    # 5. 更新去重複記錄
    sent_ids.update(new_ids)
    save_sent_ids(sent_ids)
    logger.info("已更新去重複記錄，總計 %d 篇", len(sent_ids))

    logger.info("===== NewsBot 執行結束 =====")


if __name__ == "__main__":
    main()
