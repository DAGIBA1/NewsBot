"""端到端 Integration Test — 用 mock 驗證完整資料流。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from reddit_scraper import RedditPost, CategoryPosts


def _make_post(post_id: str, sub: str = "TestSub") -> RedditPost:
    return RedditPost(
        post_id=post_id,
        title=f"Title for {post_id}",
        selftext="Content here",
        url=f"https://example.com/{post_id}",
        score=100,
        subreddit=sub,
        permalink=f"https://reddit.com/r/{sub}/{post_id}",
    )


class TestIntegration:
    @patch("main.dispatch_reports")
    @patch("main.summarize_posts")
    @patch("main.fetch_all_categories")
    def test_full_pipeline(self, mock_fetch, mock_summarize, mock_dispatch, tmp_path):
        """驗證 scraper → processor → notifier 的完整資料流。"""
        # 設定 mock 回傳
        mock_fetch.return_value = [
            CategoryPosts(
                category="AI 應用",
                emoji="\U0001f916",
                posts=[_make_post("p1", "LocalLLaMA"), _make_post("p2", "ChatGPTPro")],
            ),
        ]
        mock_summarize.return_value = [
            "[測試標題一]\n- 重點 1\n- 重點 2\n- 重點 3",
            "[測試標題二]\n- 重點 A\n- 重點 B\n- 重點 C",
        ]

        # 設定臨時的 sent_posts.json
        sent_file = tmp_path / "sent_posts.json"
        sent_file.write_text("[]", encoding="utf-8")

        with patch("main.SENT_POSTS_FILE", str(sent_file)):
            from main import main
            main()

        # 驗證各模組被正確呼叫
        mock_fetch.assert_called_once()
        assert mock_summarize.call_count == 1  # 1 個分類 = 1 次批次呼叫
        mock_dispatch.assert_called_once()

        # 驗證去重複記錄已更新
        saved = json.loads(sent_file.read_text(encoding="utf-8"))
        assert "p1" in saved
        assert "p2" in saved
