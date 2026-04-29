# PRD — Stock-Bot LINE Bot

> **版本**: v1.0  
> **建立日期**: 2026-04-29  
> **狀態**: 草稿

---

## 1. 產品概述 (Overview)

**Stock-Bot** 是一個建構在 LINE 平台上的智慧聊天機器人。它整合 **Google Gemini 2.5 Flash API** 提供自然語言對話能力，並串接即時股價資料來源，讓使用者可在 LINE 聊天視窗中完成：

1. 與 AI 進行自由閒聊或詢問一般知識。
2. 查詢任意股票（台股 / 美股）的即時或盤後股價。

---

## 2. 問題陳述與目標

| 面向 | 內容 |
|------|------|
| **痛點** | 使用者必須切換至股票 App 或搜尋引擎查詢股價，流程繁瑣 |
| **解法** | 在日常使用的 LINE 中直接查詢，降低摩擦 |
| **目標** | 打造一個輕量、即時、易用的股票查詢 + AI 對話機器人 |

---

## 3. 範圍 (Scope)

### In Scope（MVP）
- LINE Messaging API Webhook 接收與回覆
- Gemini 2.5 Flash 自然語言對話（多輪）
- 股票即時 / 收盤股價查詢（台股＋美股）
- 指令解析：辨別使用者意圖（股價查詢 vs. 一般對話）
- 基本錯誤處理與友善提示訊息

### Out of Scope（後續版本）
- 投資組合追蹤、個人化通知
- 技術分析圖表（K 線、均線）
- 帳號綁定 / 個人化設定
- 多語言支援

---

## 4. 使用者角色 (User Personas)

| 角色 | 描述 |
|------|------|
| **散戶投資人** | 偶爾查詢特定股票，不熟悉技術分析 |
| **上班族** | 利用 LINE 空檔快速確認持股狀況 |
| **學生 / 初學者** | 想了解股票但不知道從哪找資訊 |

---

## 5. 使用者故事 (User Stories)

### 5.1 AI 對話
- **US-01**：身為使用者，我可以用自然語言和 Bot 聊天，讓 Bot 用 Gemini AI 回覆，以獲得智慧對話體驗。
- **US-02**：身為使用者，我可以在同一對話窗中連續提問，Bot 能記住本次對話上下文（多輪對話）。

### 5.2 股價查詢
- **US-03**：身為使用者，我輸入「台積電股價」或「2330」，Bot 回傳 TSMC 當前股價及漲跌資訊。
- **US-04**：身為使用者，我輸入「AAPL 股價」或「蘋果股票」，Bot 回傳 Apple Inc. 當前股價及漲跌資訊。
- **US-05**：身為使用者，當股市休市或查詢符號錯誤時，Bot 回傳清楚的說明訊息。

### 5.3 指令意圖辨識
- **US-06**：身為使用者，我不需要輸入特定指令格式，Bot 能自動判斷我是要查股價還是一般聊天。

---

## 6. 功能需求 (Functional Requirements)

### FR-01：Webhook 接收與驗證
- 接收來自 LINE Platform 的 POST 請求
- 驗證 `X-Line-Signature` 確保請求合法

### FR-02：意圖辨識
- 使用 Gemini API 或關鍵字正規表達式辨別訊息是否為股價查詢
- 優先偵測股票代號（台股：4 位數字；美股：1–5 位英文字母）及「股價」、「price」等關鍵字

### FR-03：股價查詢
- 整合免費股價 API（優先選擇 **Yahoo Finance / yfinance** 或 **Alpha Vantage**）
- 回傳資料包含：股票名稱、代號、現價、漲跌金額、漲跌幅（%）、資料時間戳記

### FR-04：Gemini AI 對話
- 使用 `google-generativeai` SDK 呼叫 Gemini 2.5 Flash 模型
- 維護每位使用者的 session 對話歷史（以 `userId` 為 key，存於記憶體或 Redis）
- 預設 System Prompt 設定 Bot 角色與行為邊界

### FR-05：回覆格式化
- 股價查詢：結構化 Flex Message 或格式化文字
- 一般對話：純文字回覆
- 錯誤訊息：友善、明確

### FR-06：健康檢查端點
- 提供 `GET /health` 回傳服務狀態，便於部署監控

---

## 7. 非功能需求 (Non-Functional Requirements)

| 類別 | 需求 |
|------|------|
| **效能** | 平均回覆時間 < 3 秒（90th percentile） |
| **可用性** | 服務可用率 ≥ 99%（月計） |
| **安全性** | API 金鑰不硬編碼，透過環境變數注入；驗證 LINE Signature |
| **可擴展性** | 無狀態 Webhook 服務，可水平擴展 |
| **可維護性** | 程式碼模組化（router / service / adapter 分層） |
| **日誌** | 記錄 userId（遮罩）、意圖類型、回應時間至標準輸出 |

---

## 8. 系統架構概覽

```
LINE 使用者
    │  (HTTPS POST)
    ▼
LINE Platform
    │  Webhook
    ▼
┌─────────────────────────────┐
│  Stock-Bot Backend (Python) │
│  ┌──────────┐ ┌──────────┐  │
│  │ Webhook  │ │ Router   │  │
│  │ Handler  │─│ & Intent │  │
│  └──────────┘ └────┬─────┘  │
│              ┌─────┴──────┐ │
│    ┌─────────▼──┐  ┌──────▼──────┐ │
│    │ Gemini Svc │  │ Stock Svc   │ │
│    └─────────┬──┘  └──────┬──────┘ │
└─────────────────────────────┘
              │              │
    Gemini 2.5 Flash API   Yahoo Finance / yfinance
```

---

## 9. 技術堆疊 (Tech Stack)

| 層次 | 技術 |
|------|------|
| **語言** | Python 3.11+ |
| **Web 框架** | FastAPI |
| **LINE SDK** | `line-bot-sdk-python` |
| **AI** | `google-generativeai`（Gemini 2.5 Flash） |
| **股價資料** | `yfinance` 或 Alpha Vantage API |
| **部署** | Render / Railway / GCP Cloud Run（免費方案） |
| **環境變數管理** | `python-dotenv` |
| **對話狀態** | 記憶體 dict（MVP）；後續可升級 Redis |

---

## 10. 環境變數設計

```env
LINE_CHANNEL_SECRET=xxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxx
GEMINI_API_KEY=xxxx
STOCK_API_KEY=xxxx          # 若使用 Alpha Vantage
PORT=8000
```

---

## 11. UI / UX 設計指引

- **回覆語言**：繁體中文（預設），可跟隨使用者輸入語言切換
- **股價回覆範例**：
  ```
  📈 台積電 (2330.TW)
  現價：NT$ 980.00
  漲跌：+15.00 (+1.55%)
  更新時間：2026-04-29 09:30 (TST)
  ```
- **錯誤回覆範例**：
  ```
  ⚠️ 找不到「XYZABC」的股票資訊，請確認代號是否正確。
  ```
- **AI 對話**：使用自然口吻，避免過度制式化

---

## 12. 驗收標準 / 成功指標 (Success Metrics)

| 指標 | 目標值 |
|------|--------|
| Webhook 回覆成功率 | ≥ 99% |
| 股價查詢準確率 | ≥ 98%（比對官方資料） |
| 平均回覆時間 | < 3 秒 |
| 使用者滿意度（首月問卷） | ≥ 4.0 / 5.0 |
| MVP 上線時程 | 2 週內 |

---

## 13. 里程碑 (Milestones)

| 階段 | 內容 | 預計完成 |
|------|------|----------|
| M1 | 專案初始化、Webhook 接收驗證 | Week 1 Day 1–2 |
| M2 | Gemini AI 對話串接 | Week 1 Day 3–4 |
| M3 | 股價查詢功能 | Week 1 Day 5–7 |
| M4 | 意圖辨識整合 | Week 2 Day 1–2 |
| M5 | 測試、錯誤處理、部署 | Week 2 Day 3–5 |
| M6 | UAT & 上線 | Week 2 Day 6–7 |

---

## 14. 開放問題 (Open Questions)

1. **股價資料來源**：優先使用 `yfinance`（免費、無需 API Key），還是 Alpha Vantage（需 Key，但更穩定）？
2. **對話歷史保存**：MVP 僅保存於記憶體（重啟即清除）是否可接受？
3. **台股支援範圍**：僅上市（.TW）還是也包含上櫃（.TWO）？
4. **部署平台**：有偏好的免費雲端平台（Render / Railway / Fly.io）？
5. **LINE 帳號**：是否已建立 LINE Official Account 並取得 Channel Secret / Access Token？
