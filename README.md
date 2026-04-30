# W11 作業：股票 LINE Bot

> **繳交方式**：將你的 GitHub repo 網址貼到作業繳交區
> **作業性質**：個人作業

---

## 作業目標

利用上週設計的 Skill，開發一個股票相關的 LINE Bot。
重點不是功能多寡，而是你設計的 **Skill 品質**——Skill 寫得越具體，AI 產出的程式碼就越接近可以直接執行。

---

## 功能要求（擇一實作）

| 功能 | 說明 |
| --- | --- |
| 查詢即時價格 | 整合 yfinance 或 twstock 取得股價 |

> 以「可以執行、能回覆訊息」為目標，不需要複雜

---

## 繳交項目

你的 GitHub repo 需要包含：

| 項目 | 說明 |
| --- | --- |
| `app.py` | LINE Webhook + Gemini + SQLite 後端 |
| `requirements.txt` | 所有套件 |
| `.env.example` | 環境變數範本（不含真實 token） |
| `.agents/skills/` | 至少包含 `/linebot-implement` Skill |
| `README.md` | 本檔案（含心得報告） |
| `screenshots/chat.png` | LINE Bot 對話截圖（至少一輪完整對話） |

### Skill 要求

`.agents/skills/` 至少需要包含：

- `/linebot-implement`：產出 LINE Bot 主程式（必要）
- `/prd` 或 `/architecture`：延用上週的
- `/commit`：延用上週的

---

## 專案結構

```
your-repo/
├── .agents/
│   └── skills/
│       ├── prd/SKILL.md
│       ├── linebot-implement/SKILL.md
│       └── commit/SKILL.md
├── docs/
│   └── PRD.md
├── screenshots/
│   └── chat.png
├── app.py
├── requirements.txt
├── .env.example
└── README.md
```

> `.env` 和 `users.db` 不要 commit（加入 `.gitignore`）

---

## 啟動方式

```bash
# 1. 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env，填入三個 token

# 4. 啟動 FastAPI
uvicorn app:app --reload

# 5. 另開終端機啟動 ngrok
ngrok http 8000
# 複製 https 網址，填入 LINE Developers Console 的 Webhook URL（加上 /callback）
# 點「Verify」確認連線正常後，掃 QR Code 加好友開始測試
```

---

## 心得報告

**姓名**：許瀞云
**學號**：D1418822

**Q1. 你在 `/linebot-implement` Skill 的「注意事項」寫了哪些規則？為什麼這樣寫？**

>  1. Reply Token 只能用一次，且有 30 秒時效
>     因為30 秒是 LINE Server 的超時限制
>  2. API 金鑰絕對不能硬編碼
>     因為開發、測試、正式環境理論上要有不同的 Token。寫死就無法切換，環境變數讓你在不改程式碼的情況下切換配置。
>  3. 耗時操作必須在 30 秒內完成，或背景處理
>     如果你的 Webhook 沒在 30 秒內回，LINE 會認為傳送失敗並自動重試，造成同一則訊息被處理多次，且Reply Token 會跟著超時。
>  4. @handler.add 不能是 async def
>     因為LINE SDK 源碼裡是 func(event) 而不是 await func(event)，你的 async 函式只會被呼叫並回傳一個 coroutine 物件，然後被丟棄，事件邏輯完全沒執行，且PYTHON不會有任何錯誤提示。
>  5. Webhook URL 必須是 HTTPS
>     因為LINE 官方安全政策強制要求
>  6. 接收與傳送的 class 名稱不同
>     TextMessageContent 表示「LINE 傳來的文字訊息內容」，TextMessage 表示「你要傳出去的文字訊息物件」。混用會拿到不同的物件結構，傳入 API 就會拋 ValidationError。
>  7. 一次最多回覆 5 則訊息
>      LINE Messaging API 規格書明訂單次 Reply 最多帶 5 個 message 物件，超過就回 400 Bad Request。
---

**Q2. 你的 Skill 第一次執行後，AI 產出的程式直接能跑嗎？需要修改哪些地方？修改後有沒有更新 Skill？**

> 不能，他要LINE_CHANNEL_SECRET和LINE_CHANNEL_ACCESS_TOKEN 所以沒辦法執行，而且他的模型沒有依照前面的指示改成GEMINI 2.5 FLASH。修改後還是一直抱錯，反覆讓他修改後成功開啟了。

---

**Q3. 你遇到什麼問題是 AI 沒辦法自己解決、需要你介入處理的？**

> AI給的WEBHOOK網址一直不成功，只能一直把錯誤訊息貼給他。還有GEMINI的模型不是最新的，要手動修改。
---

**Q4. 如果你要把這個 LINE Bot 讓朋友使用，你還需要做什麼？**

> 我要增加對股票的分析、新手入門教學等功能。現在的佈署應該是臨時的，沒辦法永久使用，所以這部分應該要用其他方式才能讓所有人都能直接使用。

