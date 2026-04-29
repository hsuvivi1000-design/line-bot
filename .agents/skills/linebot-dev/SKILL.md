---
name: LINE Bot Developer
description: LINE Bot 程式碼開發指南 - line-bot-sdk-python v3 標準寫法、地雷清單、事件速查
---

# LINE Bot Developer Skill

本 skill 適用於所有 LINE Bot 程式碼的撰寫與審查階段。
**讀完本文件再開始寫任何 LINE Bot 相關程式碼。**

---

## 1. SDK 版本：v2 vs v3 差異對照

> ⚠️ 本專案使用 **line-bot-sdk-python v3**，v2 API 已全面棄用，兩者 **不相容**。

| 項目 | v2（舊，禁用） | v3（現行，必用） |
|------|---------------|-----------------|
| 套件安裝 | `pip install line-bot-sdk` | `pip install line-bot-sdk>=3.0` |
| Webhook Handler import | `from linebot import LineBotApi, WebhookHandler` | `from linebot.v3 import WebhookHandler` |
| API 客戶端 | `LineBotApi(token)` | `Configuration` + `ApiClient` + `MessagingApi` |
| 回覆訊息 | `line_bot_api.reply_message(token, msg)` | `MessagingApi.reply_message(ReplyMessageRequest(...))` |
| 事件型別 import | `from linebot.models import MessageEvent` | `from linebot.v3.webhooks import MessageEvent` |
| 訊息型別 import | `from linebot.models import TextMessage` | `from linebot.v3.messaging import TextMessage` |
| 收到文字訊息型別 | `TextMessage` (linebot.models) | `TextMessageContent` (linebot.v3.webhooks) |
| Signature 例外 | `from linebot.exceptions import InvalidSignatureError` | `from linebot.v3.exceptions import InvalidSignatureError` |

### v3 標準 import 範本

```python
# Webhook 驗證與事件接收
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    UnfollowEvent,
    PostbackEvent,
)

# 傳送訊息（Reply / Push）
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    StickerMessage,
    ImageMessage,
    FlexMessage,
    FlexContainer,
)
```

---

## 2. Webhook + Handler 標準寫法（FastAPI）

### 2.1 初始化（只做一次，放模組層級）

```python
# app/routers/webhook.py
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage,
)
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# ✅ 正確：從環境變數讀取，只初始化一次
handler = WebhookHandler(settings.line_channel_secret)
line_config = Configuration(access_token=settings.line_channel_access_token)
```

### 2.2 Webhook 路由

```python
@router.post("/webhook")
async def webhook(request: Request) -> dict:
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "ok"}   # LINE 要求必須回傳 2xx
```

### 2.3 事件 Handler 寫法

```python
# 文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def on_text_message(event: MessageEvent) -> None:
    user_id = event.source.user_id
    text    = event.message.text
    token   = event.reply_token

    reply_text = handle_logic(user_id, text)   # 你的業務邏輯

    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=reply_text)],
            )
        )

# 加好友事件
@handler.add(FollowEvent)
def on_follow(event: FollowEvent) -> None:
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="歡迎加入！輸入股票代號即可查詢股價 📈")],
            )
        )
```

### 2.4 Push Message（主動推播，不需要 reply_token）

```python
def push_message(user_id: str, text: str) -> None:
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)],
            )
        )
```

---

## 3. 常見地雷 ⚠️

### 地雷 1：Reply Token 只能用一次，且有 30 秒時效

```python
# ❌ 錯誤：reply_token 已使用或超時，會拋 LineBotApiError 400
handler.reply_message(token, msg)
handler.reply_message(token, msg)   # 第二次會失敗！

# ✅ 正確：每個 event 的 reply_token 只 reply 一次
# 若需要多次回覆，改用 push_message（需要 Messaging API 費用）
# 若 token 可能超時（耗時操作後），直接用 push_message 替代
```

### 地雷 2：API 金鑰與 Token 絕對不能寫死在程式碼

```python
# ❌ 危險：硬編碼金鑰，commit 後會外洩
handler = WebhookHandler("abc123hardcodedSecret")

# ✅ 正確：從環境變數讀取
from app.config import settings
handler = WebhookHandler(settings.line_channel_secret)
```

### 地雷 3：耗時操作（AI API、股價查詢）必須在 Handler 回傳前完成，或改為背景處理

LINE Platform 要求：**Webhook 必須在 30 秒內回傳 2xx**，否則 LINE 會重試並標記失敗。

```python
# ❌ 危險：如果 AI 或股價 API 超過 30 秒，LINE 會 timeout
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    result = slow_ai_call()       # 可能超時
    reply(event.reply_token, result)

# ✅ 方案 A：FastAPI BackgroundTasks（reply_token 已超時風險，改用 push）
from fastapi import BackgroundTasks

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    handler.handle(body.decode(), signature)
    return {"status": "ok"}

@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    user_id = event.source.user_id
    text = event.message.text
    # 立即回覆「處理中」
    quick_reply(event.reply_token, "⏳ 處理中，請稍候...")
    # 背景執行耗時任務後 push
    # （需搭配 threading 或 asyncio，reply_token 此時已失效）
    import threading
    threading.Thread(target=lambda: push_message(user_id, slow_call(text))).start()

# ✅ 方案 B（本專案採用）：同步執行，確保總時間 < 10 秒
# yfinance fast_info + Gemini Flash 通常 < 5 秒，可接受
```

### 地雷 4：Handler 函式不能是 async def

```python
# ❌ 錯誤：line-bot-sdk v3 的 @handler.add 不支援 async
@handler.add(MessageEvent, message=TextMessageContent)
async def on_text(event):   # 這個 async 會被忽略或出錯
    ...

# ✅ 正確：必須是同步函式
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    ...
```

### 地雷 5：Webhook URL 必須是 HTTPS

```
# ❌ LINE 不接受
http://127.0.0.1:8000/webhook

# ✅ 本機開發用 ngrok 建立 HTTPS 隧道
# ngrok http 8000  →  https://xxxx.ngrok-free.app/webhook
```

### 地雷 6：訊息類型接收 vs 傳送的 class 名稱不同

```python
# 接收（webhooks module）：TextMessageContent
from linebot.v3.webhooks import TextMessageContent

# 傳送（messaging module）：TextMessage
from linebot.v3.messaging import TextMessage
```

### 地雷 7：一次最多回覆 5 則訊息

```python
# ❌ 超過 5 則會拋 API 錯誤
ReplyMessageRequest(reply_token=token, messages=[msg1, msg2, ..., msg6])

# ✅ 最多 5 則，超過改用多次 push_message
ReplyMessageRequest(reply_token=token, messages=[msg1, msg2, msg3, msg4, msg5])
```

---

## 4. 所有事件類型速查

### 4.1 Message Events（訊息事件）

| 事件 import | message 參數 | 說明 |
|-------------|-------------|------|
| `MessageEvent` | `TextMessageContent` | 使用者傳文字 |
| `MessageEvent` | `ImageMessageContent` | 使用者傳圖片 |
| `MessageEvent` | `VideoMessageContent` | 使用者傳影片 |
| `MessageEvent` | `AudioMessageContent` | 使用者傳語音 |
| `MessageEvent` | `FileMessageContent` | 使用者傳檔案 |
| `MessageEvent` | `LocationMessageContent` | 使用者分享位置 |
| `MessageEvent` | `StickerMessageContent` | 使用者傳貼圖 |

```python
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent, ImageMessageContent, VideoMessageContent,
    AudioMessageContent, FileMessageContent, LocationMessageContent,
    StickerMessageContent,
)

@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event): ...

@handler.add(MessageEvent, message=ImageMessageContent)
def on_image(event): ...
```

### 4.2 非訊息事件

| 事件 | import | 說明 |
|------|--------|------|
| 加好友 | `FollowEvent` | 使用者加 Bot 為好友 |
| 封鎖/刪除 | `UnfollowEvent` | 使用者封鎖或刪除 |
| 加入群組 | `JoinEvent` | Bot 被加入群組/聊天室 |
| 離開群組 | `LeaveEvent` | Bot 被踢出群組 |
| Postback | `PostbackEvent` | 點選 Quick Reply / Flex 按鈕 |
| 位置 Beacon | `BeaconEvent` | 進入 Beacon 範圍 |
| 帳號連動 | `AccountLinkEvent` | LINE Login 帳號連動 |

```python
from linebot.v3.webhooks import (
    FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent, PostbackEvent,
)
```

### 4.3 訊息來源（Source）

```python
event.source.type      # "user" / "group" / "room"
event.source.user_id   # 使用者 ID（永遠存在）
event.source.group_id  # 群組 ID（type == "group" 時）
event.source.room_id   # 聊天室 ID（type == "room" 時）
```

---

## 5. 傳送訊息類型速查

```python
from linebot.v3.messaging import (
    TextMessage,
    StickerMessage,
    ImageMessage,
    VideoMessage,
    AudioMessage,
    LocationMessage,
    FlexMessage,
    TemplateMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    URIAction,
    PostbackAction,
)

# 文字
TextMessage(text="Hello!")

# 貼圖（packageId + stickerId 參見 LINE Sticker List）
StickerMessage(package_id="1", sticker_id="1")

# 圖片（需公開 HTTPS URL）
ImageMessage(
    original_content_url="https://example.com/image.jpg",
    preview_image_url="https://example.com/preview.jpg",
)

# 位置
LocationMessage(
    title="台北 101",
    address="台北市信義區信義路五段7號",
    latitude=25.0339639,
    longitude=121.5644722,
)

# Quick Reply（附在任何訊息後面）
TextMessage(
    text="請選擇查詢類型",
    quick_reply=QuickReply(items=[
        QuickReplyItem(action=MessageAction(label="台股", text="台股")),
        QuickReplyItem(action=MessageAction(label="美股", text="美股")),
    ]),
)
```

---

## 6. Flex Message 最小範例

```python
import json
from linebot.v3.messaging import FlexMessage, FlexContainer

bubble = {
    "type": "bubble",
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {"type": "text", "text": "台積電 (2330.TW)", "weight": "bold", "size": "lg"},
            {"type": "text", "text": "NT$ 980.00", "size": "xxl", "color": "#00B900"},
            {"type": "text", "text": "+15.00 (+1.55%)", "color": "#00B900"},
        ],
    },
}

FlexMessage(
    alt_text="台積電股價",
    contents=FlexContainer.from_dict(bubble),
)
```

---

## 7. 開發前 Checklist ✅

在開始撰寫 LINE Bot 程式碼前，確認以下項目全部完成：

### 環境設定
- [ ] 已建立 LINE Official Account（Messaging API 類型）
- [ ] 已取得 `Channel Secret`（Basic settings 頁）
- [ ] 已取得 `Channel Access Token`（Messaging API 頁 → Issue）
- [ ] 已在 `.env` 填入上述兩個值（**不得 commit**）
- [ ] `.gitignore` 已包含 `.env`
- [ ] Webhook 已在 LINE Console 啟用（Use webhook → Enabled）
- [ ] Auto-reply messages 已關閉（避免與 Bot 衝突）
- [ ] Greeting messages 依需求設定

### 程式碼
- [ ] 使用 `line-bot-sdk>=3.0`（v3）
- [ ] `WebhookHandler` 與 `Configuration` 以環境變數初始化
- [ ] Webhook 路由有做 Signature 驗證
- [ ] 所有 `@handler.add` 函式為**同步** `def`（非 async）
- [ ] 每個 reply_token 只用一次
- [ ] 單次 reply 訊息數 ≤ 5
- [ ] 耗時操作（> 5 秒）改用 push_message + 背景執行

### 本機測試
- [ ] 伺服器啟動無錯誤（`uvicorn app.main:app --reload`）
- [ ] `GET /health` 回傳 `{"status": "ok"}`
- [ ] ngrok 啟動並取得 HTTPS URL
- [ ] LINE Console Webhook URL 已更新為 ngrok URL
- [ ] 點「Verify」成功（回傳 200）
- [ ] 手機 LINE 發送測試訊息，Bot 有正確回覆

### 部署（Render）
- [ ] `requirements.txt` 包含所有依賴
- [ ] Render 環境變數已設定（不使用 .env 檔）
- [ ] Start command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] LINE Console Webhook URL 已更新為 Render 公開 URL
- [ ] 部署後再次點「Verify」成功

---

## 8. 快速除錯指引

| 症狀 | 可能原因 | 解法 |
|------|----------|------|
| Verify 回傳 400 | Signature 驗證失敗 | 確認 `LINE_CHANNEL_SECRET` 正確 |
| Verify 回傳 401 | Access Token 錯誤 | 重新 Issue Access Token |
| Bot 無回應 | Handler 未匹配事件 | 確認 `@handler.add` 的 message 參數型別正確 |
| `LineBotApiError: 400 The reply token has expired` | reply_token 超時或重用 | 確認單次使用，且耗時操作 < 30 秒 |
| `ValidationError` | Pydantic 欄位錯誤 | 檢查 v3 API 物件欄位命名（snake_case） |
| 伺服器回傳 500 | Handler 拋例外 | 加 try/except，確保永遠回傳 2xx |
| 訊息傳送但使用者沒收到 | Push 給錯誤 userId | 確認 userId 來源正確（event.source.user_id）|
