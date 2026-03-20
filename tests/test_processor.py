"""ai_processor.py 的單元測試。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_processor import FALLBACK_MESSAGE, summarize_posts, _parse_batch_response
from reddit_scraper import RedditPost


MOCK_BATCH_RESPONSE = """\
=== POST 1 ===
[AI 開源模型在本地運行的革命性突破]
- 新型量化技術讓大型語言模型能在消費級 GPU 上高效運行
- 社群分享了多個優化方案，大幅降低記憶體需求
- 這項進展可能改變 AI 產業的商業模式與使用者隱私保護

=== POST 2 ===
[測試標題二]
- 重點 A
- 重點 B
- 重點 C"""


def _make_post(title: str = "Test title", selftext: str = "Test content") -> RedditPost:
    return RedditPost(
        post_id="abc",
        title=title,
        selftext=selftext,
        url="https://example.com",
        score=100,
        subreddit="TestSub",
        permalink="https://reddit.com/r/TestSub/abc",
    )


def _make_mock_pool(response_text: str | None = MOCK_BATCH_RESPONSE, side_effect=None) -> MagicMock:
    """建立模擬的 _KeyPool。"""
    pool = MagicMock()
    client = MagicMock()
    if side_effect:
        client.models.generate_content.side_effect = side_effect
    else:
        mock_response = MagicMock()
        mock_response.text = response_text
        client.models.generate_content.return_value = mock_response
    pool.client = client
    return pool


class TestSummarizePosts:
    """summarize_posts 函式的測試。"""

    @patch("ai_processor._get_pool")
    def test_normal_batch_summary(self, mock_get_pool):
        """正常批次摘要：回傳與貼文數量相同的摘要清單。"""
        mock_get_pool.return_value = _make_mock_pool()
        posts = [_make_post("Title 1", "Content 1"), _make_post("Title 2", "Content 2")]

        results = summarize_posts(posts)

        assert len(results) == 2
        assert "[AI 開源模型" in results[0]
        assert "[測試標題二]" in results[1]

    @patch("ai_processor._get_pool")
    def test_api_timeout_returns_fallback(self, mock_get_pool):
        """API Timeout：全部回傳預設錯誤字串。"""
        mock_get_pool.return_value = _make_mock_pool(side_effect=TimeoutError("Request timed out"))
        posts = [_make_post()]

        results = summarize_posts(posts)

        assert results == [FALLBACK_MESSAGE]

    @patch("ai_processor._get_pool")
    def test_safety_block_returns_fallback(self, mock_get_pool):
        """Safety Block（回傳 None）：全部回傳預設錯誤字串。"""
        mock_get_pool.return_value = _make_mock_pool(response_text=None)
        posts = [_make_post()]

        results = summarize_posts(posts)

        assert results == [FALLBACK_MESSAGE]

    @patch("ai_processor._get_pool")
    def test_empty_selftext_still_generates(self, mock_get_pool):
        """空內文：僅傳入標題仍能生成摘要。"""
        mock_get_pool.return_value = _make_mock_pool(
            response_text="=== POST 1 ===\n[測試標題]\n- 重點 1\n- 重點 2\n- 重點 3"
        )
        posts = [_make_post("Title only post", "")]

        results = summarize_posts(posts)

        assert results[0] != FALLBACK_MESSAGE


class TestParseBatchResponse:
    """_parse_batch_response 的測試。"""

    def test_parse_correct_count(self):
        result = _parse_batch_response(MOCK_BATCH_RESPONSE, 2)
        assert len(result) == 2

    def test_parse_fills_missing(self):
        """回應不足時補齊 FALLBACK_MESSAGE。"""
        result = _parse_batch_response("=== POST 1 ===\n[標題]\n- 重點", 3)
        assert len(result) == 3
        assert result[2] == FALLBACK_MESSAGE
