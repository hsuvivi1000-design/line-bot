---
name: Data Modeler
description: 資料模型階段 - 產生 docs/MODELS.md
---
# Data Modeler

當使用者呼叫 `/models` 時，請根據架構設計與需求來規劃資料庫模型。

## 執行步驟
1. 讀取 `docs/PRD.md` 與 `docs/ARCHITECTURE.md` 以確認資料儲存需求。
2. 設計並定義資料庫架構 (Database Schema)，詳細列出：
   - 資料表 (Tables) 清單
   - 各欄位詳細定義 (名稱、資料型態、主外鍵)
   - ER Model 關聯說明
3. 產出清晰的 Markdown 表格與文件。
4. 預設將文件儲存於 `docs/MODELS.md` 中。
