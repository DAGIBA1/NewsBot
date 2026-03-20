"""reddit_scraper.py 的單元測試（JSON endpoint 版）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from reddit_scraper import CategoryPosts, RedditPost, fetch_all_categories, fetch_top_posts


def _make_reddit_json(post_ids: list[str]) -> dict:
    """建立模擬的 Reddit JSON API 回應。"""
    children = []
    for pid in post_ids:
        children.append({
            "data": {
                "id": pid,
                "title": f"Title for {pid}",
                "selftext": "Some content",
                "url": f"https://example.com/{pid}",
                "score": 100,
                "permalink": f"/r/test/comments/{pid}/test/",
            }
        })
    return {"data": {"children": children}}


def _make_session_mock(json_data: dict | None = None, side_effect=None) -> MagicMock:
    """建立模擬的 requests.Session。"""
    session = MagicMock()
    if side_effect:
        session.get.side_effect = side_effect
    else:
        mock_resp = MagicMock()
        mock_resp.json.return_value = json_data or _make_reddit_json([])
        mock_resp.raise_for_status.return_value = None
        session.get.return_value = mock_resp
    return session


class TestFetchTopPosts:
    """fetch_top_posts 函式的測試。"""

    def test_normal_fetch_returns_correct_structure(self):
        """正常抓取：回傳 3 篇貼文，結構正確。"""
        json_data = _make_reddit_json(["post_0", "post_1", "post_2"])
        session = _make_session_mock(json_data)

        posts = fetch_top_posts("LocalLLaMA", limit=3, session=session)

        assert len(posts) == 3
        assert all(isinstance(p, RedditPost) for p in posts)
        assert posts[0].post_id == "post_0"
        assert posts[0].permalink == "https://reddit.com/r/test/comments/post_0/test/"

    def test_subreddit_failure_returns_empty(self):
        """看板抓取失敗（例外），回傳空列表不崩潰。"""
        session = _make_session_mock(side_effect=Exception("Connection error"))

        posts = fetch_top_posts("PrivateSubreddit", limit=3, session=session)

        assert posts == []

    def test_empty_subreddit_returns_empty(self):
        """空看板（無貼文），回傳空列表。"""
        json_data = {"data": {"children": []}}
        session = _make_session_mock(json_data)

        posts = fetch_top_posts("EmptySub", limit=3, session=session)

        assert posts == []

    def test_deduplication_skips_sent_ids(self):
        """去重複：已推播的 post ID 會被跳過。"""
        json_data = _make_reddit_json(["post_0", "post_1", "post_2", "post_3", "post_4"])
        session = _make_session_mock(json_data)

        sent_ids = {"post_0", "post_2"}
        posts = fetch_top_posts("TestSub", limit=3, sent_ids=sent_ids, session=session)

        post_ids = {p.post_id for p in posts}
        assert "post_0" not in post_ids
        assert "post_2" not in post_ids
        assert len(posts) == 3  # 仍能湊滿 3 篇


class TestFetchAllCategories:
    """fetch_all_categories 函式的測試。"""

    def test_returns_all_categories(self, monkeypatch):
        """回傳所有分類，即使某看板失敗。"""
        call_count = 0

        def mock_fetch(subreddit_name, limit=3, sent_ids=None, session=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return []  # 模擬看板失敗後回傳空列表（實際 fetch_top_posts 內部 catch）
            return [
                RedditPost(
                    post_id=f"{subreddit_name}_{i}",
                    title=f"Title {i}",
                    selftext="Content",
                    url="https://example.com",
                    score=100,
                    subreddit=subreddit_name,
                    permalink=f"https://reddit.com/r/{subreddit_name}/{i}",
                )
                for i in range(3)
            ]

        monkeypatch.setattr("reddit_scraper.fetch_top_posts", mock_fetch)

        results = fetch_all_categories()

        assert len(results) == 4  # 4 個分類都有回傳
        assert all(isinstance(r, CategoryPosts) for r in results)
        assert results[0].category == "AI 應用"
