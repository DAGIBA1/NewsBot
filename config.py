"""集中管理所有可配置的參數。"""

import os

# --- Subreddit 分類與看板對應 ---
SUBREDDIT_MAP: dict[str, list[str]] = {
    "AI 應用": ["LocalLLaMA", "ChatGPTPro"],
    "傳統投資": ["SecurityAnalysis", "algotrading"],
    "加密貨幣": ["CryptoCurrency", "solana"],
    "國際政經": ["geopolitics", "worldnews"],
}

# --- 每個分類的 Emoji ---
CATEGORY_EMOJI: dict[str, str] = {
    "AI 應用": "\U0001f916",
    "傳統投資": "\U0001f4c8",
    "加密貨幣": "\U0001f4b0",
    "國際政經": "\U0001f30d",
}

# --- 分類 → Telegram Channel 環境變數名稱對應 ---
CATEGORY_CHANNEL_ENV: dict[str, str] = {
    "AI 應用": "TELEGRAM_CHANNEL_AI",
    "傳統投資": "TELEGRAM_CHANNEL_INVEST",
    "加密貨幣": "TELEGRAM_CHANNEL_CRYPTO",
    "國際政經": "TELEGRAM_CHANNEL_GEO",
}

# --- Reddit 抓取設定 ---
POSTS_PER_SUBREDDIT = 3
TIME_FILTER = "day"

# --- Gemini AI 設定 ---
GEMINI_MODEL = "gemini-2.0-flash"

# --- 去重複資料檔路徑 ---
SENT_POSTS_FILE = os.path.join(os.path.dirname(__file__), "data", "sent_posts.json")

# --- Telegram 訊息長度上限 ---
TELEGRAM_MESSAGE_LIMIT = 4096
