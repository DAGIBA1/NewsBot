"""notifier.py 的單元測試。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from reddit_scraper import CategoryPosts, RedditPost
from notifier import format_category_message, split_message, send_to_channel


def _make_post(post_id: str = "abc", score: int = 500) -> RedditPost:
    return RedditPost(
        post_id=post_id,
        title="Test Post Title",
        selftext="Content",
        url="https://example.com",
        score=score,
        subreddit="TestSub",
        permalink="https://reddit.com/r/test/abc",
    )


def _make_category(num_posts: int = 3) -> CategoryPosts:
    return CategoryPosts(
        category="AI 應用",
        emoji="\U0001f916",
        posts=[_make_post(f"post_{i}", score=100 * (i + 1)) for i in range(num_posts)],
    )


class TestFormatCategoryMessage:
    def test_format_includes_emoji_and_category(self):
        cat = _make_category()
        msg = format_category_message(cat)
        assert "\U0001f916" in msg
        assert "AI 應用" in msg

    def test_format_includes_all_posts(self):
        cat = _make_category(3)
        msg = format_category_message(cat)
        assert msg.count("\U0001f53c") == 3  # 3 篇貼文
        assert msg.count("\U0001f517") == 3  # 3 個連結

    def test_empty_posts_shows_no_posts_message(self):
        cat = _make_category(0)
        msg = format_category_message(cat)
        assert "今日無新貼文" in msg


class TestSplitMessage:
    def test_short_message_not_split(self):
        chunks = split_message("short message", limit=100)
        assert len(chunks) == 1

    def test_long_message_split_correctly(self):
        lines = [f"Line {i}: {'x' * 50}" for i in range(100)]
        text = "\n".join(lines)
        chunks = split_message(text, limit=500)
        assert len(chunks) > 1
        assert all(len(c) <= 500 for c in chunks)


class TestSendToChannel:
    @patch("notifier.requests.post")
    def test_successful_send(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = send_to_channel("token123", "@test_channel", "Hello")
        assert result is True
        mock_post.assert_called_once()

    @patch("notifier.requests.post")
    def test_rate_limit_retry(self, mock_post):
        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.json.return_value = {"parameters": {"retry_after": 0}}

        ok_resp = MagicMock()
        ok_resp.status_code = 200

        mock_post.side_effect = [rate_resp, ok_resp]

        result = send_to_channel("token123", "@test_channel", "Hello", max_retries=2)
        assert result is True
        assert mock_post.call_count == 2
