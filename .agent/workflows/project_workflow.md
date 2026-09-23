---
tag: "2026.09.23-current"
status: "CURRENT"
project: "AIoT L3 CWA HW1"
description: "Current five-gate Taiwan Weather GIS development workflow"
source: ".agent/workflows/project_workflow.md"
---

# CURRENT TAG — 2026.09.23

> **Status: CURRENT / ACTIVE**
>
> This is the current project workflow baseline. Antigravity and future development should follow this version unless a newer tagged workflow explicitly supersedes it.

# Taiwan Weather GIS — Project Workflow

## Governing Rule

嚴格依序執行：

```text
Gate 1 CWA API
 → Gate 2 Database
 → Gate 3 Local Taiwan GIS
 → Gate 4 GitHub
 → Gate 5 Vercel
```

**DO NOT BUILD EVERYTHING AT ONCE.**

每個 Gate 必須 `BUILD → RUN → TEST → VERIFY → PASS`。FAIL 時停留在該 Gate 修正。不得使用 mock/fake weather data。

## Gate 1 — CWA API

Goal: 從 CWA Open Data API 取得真實 Forecast JSON。

1. 確認 Dataset 與 endpoint。
2. 從 `.env` 讀取 `CWA_API_KEY`；不得輸出完整 key。
3. 發送真實 HTTP request。
4. 驗證 HTTP status。
5. 依實際 response 解析 JSON，不猜 schema。
6. 先驗證一個地區，例如臺中市。
7. 輸出 Location、Forecast Time、Weather、MinT、MaxT；Dataset 有提供時再輸出 PoP。
8. 確認後續所需其他台灣地區也存在。
9. 實際 RUN 並留下驗證結果。

禁止實作 Database、GIS、GitHub deployment、Vercel。

只有全部成功才回報：`GATE 1 = PASS`。

## Gate 2 — Database

前提：Gate 1 PASS。

將真實 CWA response 做 ETL 並存入 SQLite。建立 schema、資料驗證與 duplicate strategy，以 SQL SELECT 驗證指定地區及多地區資料。

禁止開始 GIS。

完成才回報：`GATE 2 = PASS`。

## Gate 3 — Local Taiwan GIS

前提：Gate 2 PASS。

依序完成：

```text
3A Taiwan Map
3B One Marker
3C Weather Popup
3D Taiwan Locations
3E Database → GIS
3F Taiwan GeoJSON
3G Interactive Dashboard
```

GIS 優先使用 Leaflet + OpenStreetMap + Taiwan GeoJSON。Weather 必須來自 Database。

完成才回報：`GATE 3 = PASS`。

## Gate 4 — GitHub

前提：Gate 3 PASS。

整理 repository、README/design、requirements 與安全設定。Push 前確認 `.env` 與任何 secret 不在 Git history/current files。

完成才回報：`GATE 4 = PASS`。

## Gate 5 — Vercel

前提：Gate 4 PASS。

連接 GitHub → Vercel，設定 Environment Variables，完成 build/deploy，驗證 public URL，並測試後續 GitHub push 能觸發 auto deployment。

Local SQLite 不視為 Vercel 的永久 Production Database；若需要線上持續寫入，另採 Cloud Database。

完成才回報：`GATE 5 = PASS`。

## Final

只有五 Gate 全 PASS 才回報：

```text
DIC-2 / AIoT L3 CWA HW1 = COMPLETE
```

## Current Baseline

```text
TAG: 2026.09.23-current
STATUS: CURRENT
MAINLINE:
CWA API → Database → Local Taiwan GIS → GitHub → Vercel
```
