"""config.py 的單元測試。"""

from config import CATEGORY_CHANNEL_ENV, CATEGORY_EMOJI, SUBREDDIT_MAP


class TestConfig:
    def test_all_categories_have_emoji(self):
        for cat in SUBREDDIT_MAP:
            assert cat in CATEGORY_EMOJI, f"分類 '{cat}' 缺少 Emoji 對應"

    def test_all_categories_have_channel_env(self):
        for cat in SUBREDDIT_MAP:
            assert cat in CATEGORY_CHANNEL_ENV, f"分類 '{cat}' 缺少 Channel 環境變數對應"

    def test_subreddit_map_not_empty(self):
        assert len(SUBREDDIT_MAP) > 0
        for cat, subs in SUBREDDIT_MAP.items():
            assert len(subs) > 0, f"分類 '{cat}' 沒有任何看板"
