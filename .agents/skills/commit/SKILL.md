---
name: Git Committer
description: 提交推送階段 - 執行 git commit + push
---
# Git Committer

當使用者呼叫 `/commit` 時，請協助進行版本控制的提交與推送。

## 執行步驟
1. 檢視當前專案修改了哪些檔案 (Git Status)。
2. 提供一段符合慣例 (如 feat:, fix:, docs:) 且描述精準的 Git Commit Message 建議給使用者。
3. 引導或主動執行 `git add .`、`git commit -m "..."` 及 `git push` 指令，將進度保存並上推。
