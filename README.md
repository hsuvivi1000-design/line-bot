# Stock-Bot 📈

> LINE Bot × Gemini 2.5 Flash × 即時股價查詢

## 功能

- 🤖 **AI 對話**：由 Gemini 2.5 Flash 驅動的多輪自然語言聊天
- 📈 **股價查詢**：支援台股（2330.TW）與美股（AAPL）即時報價
- 🧠 **意圖辨識**：自動判斷是查股票還是一般聊天，無需輸入指令

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的 API Key
```

### 3. 啟動服務

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. 設定 LINE Webhook URL

在 LINE Developers Console 設定：
```
https://<your-domain>/webhook
```

> 本機開發可使用 [ngrok](https://ngrok.com/) 建立公開 HTTPS 隧道：
> ```bash
> ngrok http 8000
> ```

## 環境變數

| 變數名稱 | 必要 | 說明 |
|----------|------|------|
| `LINE_CHANNEL_SECRET` | ✅ | LINE Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | LINE Channel Access Token |
| `GEMINI_API_KEY` | ✅ | Google AI Studio API Key |
| `PORT` | ❌ | 服務 port，預設 8000 |
| `SESSION_MAX_HISTORY` | ❌ | 每位使用者保留輪數，預設 20 |

## 目錄結構

```
stock-bot/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 環境變數管理
│   ├── handlers/            # LINE Webhook 事件處理
│   ├── routers/             # API 路由
│   ├── services/            # 業務邏輯
│   ├── adapters/            # 外部 API 封裝
│   └── models/              # 資料模型
├── tests/                   # 單元測試
├── docs/                    # 文件
├── .env.example
├── requirements.txt
└── README.md
```

## 查詢範例

| 輸入 | Bot 回應 |
|------|----------|
| `台積電股價` | 📈 台積電 (2330.TW) 現價 NT$... |
| `AAPL` | 📈 Apple Inc. (AAPL) 現價 $... |
| `最近AI股怎樣？` | Gemini AI 回覆 |
| `你好` | Gemini AI 回覆 |

## 技術堆疊

- **框架**：FastAPI + Uvicorn
- **LINE**：line-bot-sdk-python v3
- **AI**：Google Gemini 2.5 Flash
- **股價**：yfinance (Yahoo Finance)
- **部署**：Render
