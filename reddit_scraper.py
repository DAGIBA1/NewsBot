"""Reddit 抓取模組 — 從指定看板取得熱門貼文。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import praw

from config import (
    CATEGORY_EMOJI,
    POSTS_PER_SUBREDDIT,
    SUBREDDIT_MAP,
    TIME_FILTER,
)

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """單篇 Reddit 貼文的結構化資料。"""

    post_id: str
    title: str
    selftext: str
    url: str
    score: int
    subreddit: str
    permalink: str


@dataclass
class CategoryPosts:
    """單一分類下的所有貼文。"""

    category: str
    emoji: str
    posts: list[RedditPost] = field(default_factory=list)


def _create_reddit_client() -> praw.Reddit:
    """建立 Reddit API 客戶端。"""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "newsbot/1.0"),
    )


def fetch_top_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    limit: int = POSTS_PER_SUBREDDIT,
    sent_ids: set[str] | None = None,
) -> list[RedditPost]:
    """抓取指定看板的熱門貼文，自動跳過已推播的文章。"""
    sent_ids = sent_ids or set()
    posts: list[RedditPost] = []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        # 多抓一些以補足被去重複過濾掉的文章
        for submission in subreddit.top(time_filter=TIME_FILTER, limit=limit + len(sent_ids)):
            if submission.id in sent_ids:
                logger.debug("跳過已推播文章: %s", submission.id)
                continue
            posts.append(
                RedditPost(
                    post_id=submission.id,
                    title=submission.title,
                    selftext=submission.selftext or "",
                    url=submission.url,
                    score=submission.score,
                    subreddit=subreddit_name,
                    permalink=f"https://reddit.com{submission.permalink}",
                )
            )
            if len(posts) >= limit:
                break
    except Exception:
        logger.exception("抓取 r/%s 失敗，跳過此看板", subreddit_name)

    return posts


def fetch_all_categories(
    reddit: praw.Reddit | None = None,
    sent_ids: set[str] | None = None,
) -> list[CategoryPosts]:
    """遍歷所有分類看板，回傳結構化資料。"""
    if reddit is None:
        reddit = _create_reddit_client()

    results: list[CategoryPosts] = []

    for category, subreddits in SUBREDDIT_MAP.items():
        cat = CategoryPosts(
            category=category,
            emoji=CATEGORY_EMOJI.get(category, ""),
        )
        for sub_name in subreddits:
            cat.posts.extend(fetch_top_posts(reddit, sub_name, sent_ids=sent_ids))
        results.append(cat)

    return results
