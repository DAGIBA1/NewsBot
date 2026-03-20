"""ai_processor.py 的單元測試。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_processor import FALLBACK_MESSAGE, summarize_post


MOCK_RESPONSE = """\
[AI 開源模型在本地運行的革命性突破]
- 新型量化技術讓大型語言模型能在消費級 GPU 上高效運行
- 社群分享了多個優化方案，大幅降低記憶體需求
- 這項進展可能改變 AI 產業的商業模式與使用者隱私保護"""


def _make_mock_client(response_text: str | None = MOCK_RESPONSE, side_effect=None) -> MagicMock:
    """建立模擬的 genai.Client。"""
    client = MagicMock()
    if side_effect:
        client.models.generate_content.side_effect = side_effect
    else:
        mock_response = MagicMock()
        mock_response.text = response_text
        client.models.generate_content.return_value = mock_response
    return client


class TestSummarizePost:
    """summarize_post 函式的測試。"""

    def test_normal_summary(self):
        """正常摘要：回傳標準格式的翻譯摘要。"""
        client = _make_mock_client()

        result = summarize_post("LocalLLaMA breakthrough", "Some long content here...", client=client)

        assert "[AI 開源模型" in result
        assert "- " in result
        client.models.generate_content.assert_called_once()

    def test_api_timeout_returns_fallback(self):
        """API Timeout：回傳預設錯誤字串。"""
        client = _make_mock_client(side_effect=TimeoutError("Request timed out"))

        result = summarize_post("Test title", "Test content", client=client)

        assert result == FALLBACK_MESSAGE

    def test_safety_block_returns_fallback(self):
        """Safety Block（回傳 None）：回傳預設錯誤字串。"""
        client = _make_mock_client(response_text=None)

        result = summarize_post("Controversial title", "Blocked content", client=client)

        assert result == FALLBACK_MESSAGE

    def test_empty_selftext_still_generates(self):
        """空內文：僅傳入標題仍能生成摘要。"""
        client = _make_mock_client(response_text="[測試標題]\n- 重點 1\n- 重點 2\n- 重點 3")

        result = summarize_post("Title only post", "", client=client)

        assert result != FALLBACK_MESSAGE
        # 驗證傳給 API 的 content 不含「內文」字段
        call_args = client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get("contents")
        assert "內文" not in contents
