# ARCHITECTURE — Stock-Bot LINE Bot

> **版本**: v1.0  
> **建立日期**: 2026-04-29  
> **依據**: docs/PRD.md v1.0

---

## 1. 架構總覽

Stock-Bot 採用 **單體式後端（Monolithic Backend）+ 無狀態 Webhook** 架構。  
對外只暴露一個 HTTPS 端點給 LINE Platform，內部依功能垂直切分為三層：

```
┌─────────────────────────────────────────────────────────────┐
│                        LINE Platform                        │
│              (Webhook POST / Reply API)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────┐
│                  Stock-Bot Backend (FastAPI)                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Presentation Layer                    │    │
│  │  POST /webhook   GET /health                        │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                   │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │               Application Layer                     │    │
│  │  WebhookHandler → SignatureVerifier → MessageRouter │    │
│  │                         │                           │    │
│  │          ┌──────────────┴──────────────┐            │    │
│  │          │         IntentClassifier    │            │    │
│  │          └──────┬──────────────┬───────┘            │    │
│  └─────────────────┼──────────────┼────────────────────┘    │
│                    │              │                          │
│  ┌─────────────────▼──┐  ┌───────▼────────────────────┐    │
│  │   Service Layer    │  │     Service Layer           │    │
│  │   GeminiService    │  │     StockService            │    │
│  └─────────────────┬──┘  └───────┬────────────────────┘    │
│                    │              │                          │
│  ┌─────────────────▼──┐  ┌───────▼────────────────────┐    │
│  │   Adapter Layer    │  │     Adapter Layer           │    │
│  │   GeminiAdapter    │  │     YFinanceAdapter         │    │
│  └─────────────────┬──┘  └───────┬────────────────────┘    │
└────────────────────┼─────────────┼────────────────────────┘
                     │             │
          Gemini 2.5 Flash API   yfinance (Yahoo Finance)
```

---

## 2. 技術選型

### 2.1 後端框架

| 項目 | 選擇 | 理由 |
|------|------|------|
| 語言 | **Python 3.11+** | 生態最完整（line-bot-sdk、google-generativeai、yfinance 均為 Python 原生） |
| Web 框架 | **FastAPI** | 非同步支援、自動 OpenAPI 文件、型別安全 |
| ASGI Server | **Uvicorn** | FastAPI 官方推薦，效能優異 |

### 2.2 外部服務

| 項目 | 選擇 | 理由 |
|------|------|------|
| LINE 整合 | `line-bot-sdk-python` v3 | 官方 SDK，內建 Signature 驗證 |
| AI 對話 | `google-generativeai` + Gemini 2.5 Flash | 高速、低延遲，符合 PRD 要求 |
| 股價資料 | `yfinance` | 免費、無需 API Key、支援台股(.TW)與美股 |

### 2.3 狀態管理

| 項目 | MVP | 未來擴充 |
|------|-----|----------|
| 對話歷史 | 記憶體 `dict[userId → history]` | Redis（TTL 24h） |
| 設定 | `.env` + `python-dotenv` | AWS Secrets Manager / GCP Secret Manager |

### 2.4 部署

| 項目 | 選擇 |
|------|------|
| 平台 | **Render**（免費 Web Service） |
| 反向代理 | Render 內建 HTTPS（自動 TLS） |
| CI/CD | GitHub → Render Auto-Deploy |

---

## 3. 系統組件說明

### 3.1 Presentation Layer

**`POST /webhook`**
- 接收 LINE Platform 傳入的事件（TextMessage）
- 交由 `WebhookHandler` 處理，並於 5 秒內回傳 HTTP 200（LINE 要求）
- 實際回覆透過 LINE Reply API 非同步傳送

**`GET /health`**
- 回傳 `{"status": "ok", "timestamp": "..."}` 供部署平台健康檢查

---

### 3.2 Application Layer

#### WebhookHandler
- 呼叫 `line-bot-sdk` 驗證 `X-Line-Signature`
- 解析事件類型，目前只處理 `MessageEvent` + `TextMessageContent`
- 擷取 `userId`、`replyToken`、`text` 轉交 `MessageRouter`

#### MessageRouter
- 呼叫 `IntentClassifier` 取得意圖標籤
- 依標籤分派至對應 Service

#### IntentClassifier
意圖辨識採**兩段式**策略，兼顧速度與準確性：

```
輸入訊息
  │
  ▼
① Regex 快速比對
  ├─ 台股代號：r'\b\d{4,5}[A-Z]?\b'（如 2330、00878）
  ├─ 美股代號：r'\b[A-Z]{1,5}\b'（如 AAPL、TSLA）
  └─ 關鍵字：股價 / 漲跌 / price / stock
  │
  ├─ 命中 → 意圖 = STOCK_QUERY
  │
  └─ 未命中
       │
       ▼
    ② Gemini Function Calling（或 Zero-shot Prompt）
       └─ 判斷是否為股票查詢意圖
           ├─ 是 → STOCK_QUERY（含解析出的股票代號）
           └─ 否 → CHAT
```

---

### 3.3 Service Layer

#### GeminiService
- 維護 `session_store: dict[userId, list[Content]]` 儲存多輪對話歷史
- 每次對話將歷史 + 新訊息組合後送至 Gemini API
- System Prompt 定義 Bot 角色：「你是 Stock-Bot，一個友善的投資助理，能回答一般問題及查詢股票」

```python
# 偽代碼
async def chat(user_id: str, text: str) -> str:
    history = session_store.get(user_id, [])
    response = await gemini_client.generate(
        model="gemini-2.5-flash",
        system=SYSTEM_PROMPT,
        history=history,
        message=text,
    )
    session_store[user_id] = history + [user_msg, model_msg]
    return response.text
```

#### StockService
- 接收股票代號（含後綴，如 `2330.TW`、`AAPL`）
- 透過 `YFinanceAdapter` 取得報價
- 格式化回覆文字（含 emoji、漲跌顏色符號）

---

### 3.4 Adapter Layer

#### YFinanceAdapter
```python
import yfinance as yf

async def get_quote(symbol: str) -> StockQuote:
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    return StockQuote(
        symbol=symbol,
        name=info.get("shortName", symbol),
        price=info["last_price"],
        change=info["last_price"] - info["previous_close"],
        change_pct=...,
        timestamp=datetime.now(),
    )
```

**台股代號對應**：使用者輸入 `2330` → 系統補後綴為 `2330.TW`

---

## 4. 資料流向

### 4.1 股價查詢流程

```
用戶輸入「台積電股價」
    │
    ▼
LINE Platform → POST /webhook
    │
    ▼
WebhookHandler（驗簽名）
    │
    ▼
IntentClassifier
  └─ Regex 命中「股價」+ 可能的代號
  └─ 意圖：STOCK_QUERY，symbol：2330（或需 Gemini 二次解析）
    │
    ▼
StockService.get_quote("2330.TW")
    │
    ▼
YFinanceAdapter → yfinance API
    │
    ▼
格式化回覆訊息
    │
    ▼
LINE Reply API → 用戶
```

### 4.2 AI 對話流程

```
用戶輸入「最近市場怎樣？」
    │
    ▼
LINE Platform → POST /webhook
    │
    ▼
IntentClassifier → CHAT
    │
    ▼
GeminiService.chat(userId, text)
  ├─ 讀取 session_store[userId]（對話歷史）
  ├─ 送至 Gemini 2.5 Flash API
  └─ 更新 session_store[userId]
    │
    ▼
LINE Reply API → 用戶
```

---

## 5. 資料模型

### StockQuote

```python
@dataclass
class StockQuote:
    symbol: str        # 股票代號，如 "2330.TW"
    name: str          # 股票名稱，如 "Taiwan Semiconductor"
    price: float       # 現價
    change: float      # 漲跌金額
    change_pct: float  # 漲跌百分比
    timestamp: datetime  # 資料時間
    currency: str = "TWD"  # 幣別
```

### ChatMessage（Gemini history item）

```python
# 使用 google.generativeai.types.ContentDict
{
    "role": "user" | "model",
    "parts": [{"text": "..."}]
}
```

---

## 6. 目錄結構

```
stock-bot/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 應用入口，路由定義
│   ├── config.py                # 環境變數讀取（pydantic-settings）
│   │
│   ├── handlers/
│   │   └── webhook_handler.py   # LINE Webhook 事件處理
│   │
│   ├── routers/
│   │   ├── webhook.py           # POST /webhook 路由
│   │   └── health.py            # GET /health 路由
│   │
│   ├── services/
│   │   ├── intent_classifier.py # 意圖辨識（Regex + Gemini）
│   │   ├── gemini_service.py    # AI 對話邏輯 + session 管理
│   │   └── stock_service.py     # 股價查詢 + 格式化
│   │
│   ├── adapters/
│   │   ├── yfinance_adapter.py  # yfinance 封裝
│   │   └── gemini_adapter.py    # google-generativeai 封裝
│   │
│   └── models/
│       └── stock_quote.py       # StockQuote dataclass
│
├── tests/
│   ├── test_intent_classifier.py
│   ├── test_stock_service.py
│   └── test_gemini_service.py
│
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
│
├── .env.example                 # 環境變數範本（不含機密值）
├── .env                         # 實際機密（加入 .gitignore）
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 7. 環境變數

| 變數名稱 | 必要 | 說明 |
|----------|------|------|
| `LINE_CHANNEL_SECRET` | ✅ | LINE Channel Secret（Signature 驗證用） |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | LINE Channel Access Token（Reply API 用） |
| `GEMINI_API_KEY` | ✅ | Google AI Studio API Key |
| `PORT` | ❌ | 服務監聽 port，預設 `8000` |
| `LOG_LEVEL` | ❌ | 日誌等級，預設 `INFO` |
| `SESSION_MAX_HISTORY` | ❌ | 每位使用者保留最多幾輪對話，預設 `20` |

---

## 8. 部署架構

```
開發者 (Local)
    │  git push
    ▼
GitHub Repository
    │  Auto-Deploy Webhook
    ▼
Render Web Service
  ├─ Build: pip install -r requirements.txt
  └─ Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    │
    │  HTTPS (Render 自動 TLS)
    ▼
LINE Platform
    │  Webhook URL: https://<your-app>.onrender.com/webhook
    ▼
LINE 使用者
```

---

## 9. 安全考量

| 風險 | 對策 |
|------|------|
| 偽造 Webhook 請求 | `line-bot-sdk` 驗證 HMAC-SHA256 Signature |
| API Key 外洩 | 所有 Key 存於環境變數，`.env` 列入 `.gitignore` |
| Prompt Injection | System Prompt 設定明確邊界；輸入長度限制 1000 字元 |
| 過度 API 呼叫 | 每位使用者每分鐘限制 10 次請求（In-Memory Rate Limiter） |
| 股票代號 Injection | 正規化代號後才傳入 yfinance（字母＋數字白名單） |

---

## 10. 非功能需求對應

| NFR | 實作方式 |
|-----|----------|
| 回覆時間 < 3s | yfinance `fast_info`（快取機制）；Gemini Flash 低延遲模型 |
| 可用率 ≥ 99% | Render 自動重啟；Webhook 即時回 200 後非同步處理 |
| 水平擴展 | 無狀態設計（session 存記憶體，未來遷移 Redis 即可） |
| 日誌 | uvicorn access log + structlog，userId 僅保留前 6 碼 |

---

## 11. 未來擴充路徑

```
MVP
 │
 ├─ Phase 2：Redis 持久化 session + 上櫃股(.TWO)支援
 ├─ Phase 3：LINE Flex Message 美化股價卡片
 ├─ Phase 4：個人化持股追蹤（PostgreSQL）
 └─ Phase 5：K 線圖生成（matplotlib → 圖片回傳）
```
