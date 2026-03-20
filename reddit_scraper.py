"""Reddit 抓取模組 — 透過公開 JSON endpoint 從指定看板取得熱門貼文（免 API Key）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests

from config import (
    CATEGORY_EMOJI,
    POSTS_PER_SUBREDDIT,
    SUBREDDIT_MAP,
    TIME_FILTER,
)

logger = logging.getLogger(__name__)

REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/top.json"
USER_AGENT = "newsbot/1.0 (Reddit Daily Digest Bot)"
REQUEST_TIMEOUT = 15


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


def fetch_top_posts(
    subreddit_name: str,
    limit: int = POSTS_PER_SUBREDDIT,
    sent_ids: set[str] | None = None,
    session: requests.Session | None = None,
) -> list[RedditPost]:
    """抓取指定看板的熱門貼文，自動跳過已推播的文章。"""
    sent_ids = sent_ids or set()
    posts: list[RedditPost] = []

    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

    try:
        url = REDDIT_JSON_URL.format(subreddit=subreddit_name)
        resp = session.get(
            url,
            params={"t": TIME_FILTER, "limit": limit + len(sent_ids)},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            post_id = post_data.get("id", "")

            if post_id in sent_ids:
                logger.debug("跳過已推播文章: %s", post_id)
                continue

            posts.append(
                RedditPost(
                    post_id=post_id,
                    title=post_data.get("title", ""),
                    selftext=post_data.get("selftext", ""),
                    url=post_data.get("url", ""),
                    score=post_data.get("score", 0),
                    subreddit=subreddit_name,
                    permalink=f"https://reddit.com{post_data.get('permalink', '')}",
                )
            )
            if len(posts) >= limit:
                break

    except Exception:
        logger.exception("抓取 r/%s 失敗，跳過此看板", subreddit_name)

    return posts


def fetch_all_categories(
    sent_ids: set[str] | None = None,
) -> list[CategoryPosts]:
    """遍歷所有分類看板，回傳結構化資料。"""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: list[CategoryPosts] = []

    for category, subreddits in SUBREDDIT_MAP.items():
        cat = CategoryPosts(
            category=category,
            emoji=CATEGORY_EMOJI.get(category, ""),
        )
        for sub_name in subreddits:
            cat.posts.extend(fetch_top_posts(sub_name, sent_ids=sent_ids, session=session))
        results.append(cat)

    return results
