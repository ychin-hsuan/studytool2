# 📄 StudyTool2 — AI PDF 考卷解題工具

> 上傳 PDF 考卷，讓 AI 自動找出所有題目並逐題提供詳細解答與解析

---

## ✨ 功能特色

- **📥 PDF 上傳解析** — 支援上傳最大 20MB、最多 50 頁的 PDF 考卷
- **🔍 雙模式辨識** — 自動判斷 PDF 類型：
  - 文字型 PDF → 直接提取文字送出分析
  - 掃描 / 手寫型 PDF → 轉換為圖片，使用 Claude Vision OCR 辨識
- **🤖 AI 逐題解答** — 透過 Claude Sonnet 模型，自動找出選擇題、填充題、問答題、計算題，並附上詳細解析
- **💬 追問功能** — 對任一題的解答有疑問，可直接向 AI 追問深入說明
- **⚡ 串流回應** — Server-Sent Events（SSE）即時串流顯示解題過程，無需等待
- **🔒 安全防護** — 速率限制、CORS 管控、安全標頭（CSP、X-Frame-Options）一應俱全

---

## 🏗️ 技術架構

```
studytool2/
│
├── app.py              # FastAPI 主應用程式（路由、AI 串流邏輯）
├── templates/
│   └── index.html      # 前端頁面（HTML + 內嵌 CSS/JS）
├── requirements.txt    # Python 套件相依清單
├── render.yaml         # Render 雲端部署設定
├── .env.example        # 環境變數範本
└── .gitignore
```

### API 端點

| Method | 路徑 | 說明 | 速率限制 |
|--------|------|------|---------|
| `GET` | `/` | 前端頁面 | — |
| `POST` | `/upload` | 上傳並解析 PDF | 10 次/分鐘 |
| `POST` | `/solve` | 對 PDF 內容進行 AI 解題（SSE 串流） | 5 次/分鐘 |
| `POST` | `/chat` | 對題目解答進行追問（SSE 串流） | 20 次/分鐘 |

---

## 🚀 快速開始

### 前置需求

- Python 3.11 以上
- [Anthropic API Key](https://console.anthropic.com/)

### 本地安裝與執行

1. **Clone 專案**
   ```bash
   git clone https://github.com/ychin-hsuan/studytool2.git
   cd studytool2
   ```

2. **建立虛擬環境並安裝套件**
   ```bash
   python -m venv venv
   source venv/bin/activate       # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **設定環境變數**
   ```bash
   cp .env.example .env
   ```
   編輯 `.env`，填入你的 Anthropic API Key：
   ```env
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
   ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
   ```

4. **啟動伺服器**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

5. 開啟瀏覽器前往 `http://localhost:8000`

---

## ☁️ 部署到 Render

本專案已包含 `render.yaml`，可直接一鍵部署到 [Render](https://render.com/)。

1. 將此 repo 連結到 Render
2. 在 Render 後台設定環境變數：
   - `ANTHROPIC_API_KEY`
   - `ALLOWED_ORIGINS`（填入你的 Render 服務網址）
3. Render 會自動讀取 `render.yaml` 完成部署

---

## 🛡️ 安全限制

| 項目 | 限制 |
|------|------|
| 檔案大小 | 最大 20 MB |
| 頁數上限 | 最多 50 頁 |
| 文字長度 | 最多 200,000 字元 |
| 圖片頁數 | 最多 50 張（Vision 模式） |
| API 速率 | 整體 300 次/小時；/solve 5 次/分鐘 |

---

## 🔧 技術棧

| 類別 | 使用技術 |
|------|---------|
| 後端框架 | FastAPI 0.115 |
| ASGI 伺服器 | Uvicorn |
| AI 模型 | Claude Sonnet（`claude-sonnet-4-6`） |
| PDF 解析 | PyMuPDF（fitz）|
| 速率限制 | SlowAPI |
| 前端 | 純 HTML / CSS / JavaScript（SSE）|
| 部署 | Render |

---

## 💡 使用方式

1. 開啟網頁，點選右上角 ⚙ 設定你的 **Anthropic API Key**
2. 點擊「選擇 PDF 檔案」上傳考卷
3. 系統自動判斷文字型或掃描型並進行解析
4. 點擊「開始解題」，AI 即時串流輸出逐題解答
5. 對某題有疑問，點擊追問功能輸入問題，AI 進一步說明

---

