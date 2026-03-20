"""reddit_scraper.py 的單元測試。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from reddit_scraper import CategoryPosts, RedditPost, fetch_all_categories, fetch_top_posts


def _make_submission(post_id: str, title: str = "Test", score: int = 100) -> MagicMock:
    """建立模擬的 praw Submission 物件。"""
    sub = MagicMock()
    sub.id = post_id
    sub.title = title
    sub.selftext = "Some content"
    sub.url = f"https://example.com/{post_id}"
    sub.score = score
    sub.permalink = f"/r/test/comments/{post_id}/test/"
    return sub


def _make_reddit_mock(submissions: list[MagicMock]) -> MagicMock:
    """建立模擬的 praw.Reddit 物件。"""
    reddit = MagicMock()
    subreddit = MagicMock()
    subreddit.top.return_value = iter(submissions)
    reddit.subreddit.return_value = subreddit
    return reddit


class TestFetchTopPosts:
    """fetch_top_posts 函式的測試。"""

    def test_normal_fetch_returns_correct_structure(self):
        """正常抓取：回傳 3 篇貼文，結構正確。"""
        submissions = [_make_submission(f"post_{i}") for i in range(3)]
        reddit = _make_reddit_mock(submissions)

        posts = fetch_top_posts(reddit, "LocalLLaMA", limit=3)

        assert len(posts) == 3
        assert all(isinstance(p, RedditPost) for p in posts)
        assert posts[0].post_id == "post_0"
        assert posts[0].permalink == "https://reddit.com/r/test/comments/post_0/test/"

    def test_subreddit_failure_returns_empty(self):
        """看板抓取失敗（例外），回傳空列表不崩潰。"""
        reddit = MagicMock()
        reddit.subreddit.side_effect = Exception("API error")

        posts = fetch_top_posts(reddit, "PrivateSubreddit", limit=3)

        assert posts == []

    def test_empty_subreddit_returns_empty(self):
        """空看板（無貼文），回傳空列表。"""
        reddit = _make_reddit_mock([])

        posts = fetch_top_posts(reddit, "EmptySub", limit=3)

        assert posts == []

    def test_deduplication_skips_sent_ids(self):
        """去重複：已推播的 post ID 會被跳過。"""
        submissions = [_make_submission(f"post_{i}") for i in range(5)]
        reddit = _make_reddit_mock(submissions)

        sent_ids = {"post_0", "post_2"}
        posts = fetch_top_posts(reddit, "TestSub", limit=3, sent_ids=sent_ids)

        post_ids = {p.post_id for p in posts}
        assert "post_0" not in post_ids
        assert "post_2" not in post_ids
        assert len(posts) == 3  # 仍能湊滿 3 篇


class TestFetchAllCategories:
    """fetch_all_categories 函式的測試。"""

    def test_returns_all_categories(self):
        """回傳所有分類，即使某看板失敗。"""
        submissions = [_make_submission(f"post_{i}") for i in range(3)]

        call_count = 0

        def subreddit_side_effect(name):
            nonlocal call_count
            call_count += 1
            # 讓第 2 個看板失敗
            if call_count == 2:
                raise Exception("API error")
            sub = MagicMock()
            sub.top.return_value = iter([_make_submission(f"{name}_{i}") for i in range(3)])
            return sub

        reddit = MagicMock()
        reddit.subreddit.side_effect = subreddit_side_effect

        results = fetch_all_categories(reddit=reddit)

        assert len(results) == 4  # 4 個分類都有回傳
        assert all(isinstance(r, CategoryPosts) for r in results)
        # 第一個分類的第一個看板成功，第二個看板失敗
        assert results[0].category == "AI 應用"
