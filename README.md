# 台灣投信 ETF 持股明細與比例自動採集系統

基於 Python 與 Reverse API 技術，自動抓取台灣各大投信發行之國內 ETF 每日持股明細、股數與權重比例，並持久化至關聯式資料庫（SQLite / PostgreSQL），支援 GitHub Actions 每日盤後自動排程更新。

---

## 🌟 功能特點

- **全市場涵蓋**：支援臺灣證交所（TWSE）全體 240+ 檔 ETF（0050、0056、00878、00919、00929、006208、00713 等）。
- **結構化資料庫**：內建 SQLAlchemy ORM 模型（`etf_funds` 與 `etf_holdings`），具備複合唯一索引（`uq_etf_date_stock`），避免重複寫入。
- **跨 ETF 個股搜尋**：可一鍵查詢指定股票（如「台積電」、「聯發科」、「鴻海」）在全市場各檔 ETF 中的持股比例與配置排名。
- **雙格式儲存**：同時更新 SQLite 資料庫（`etf_data.db`）並匯出 UTF-8 帶 BOM 的 CSV 檔案（`data/etf_holdings_latest.csv`），方便 Excel 開啟與 Git 版本追蹤。
- **GitHub Actions 自動化**：每日台股收盤後（週一至週五 18:30 台灣時間）自動觸發抓取，並自動 Commit 推送回儲存庫。

---

## 🚀 本地快速使用

### 1. 啟用虛擬環境
```bash
# Windows
.\.venv\Scripts\activate
```

### 2. 常用操作指令

```bash
# 抓取指定 ETF 並入庫 (例如: 0050 00878 00919)
python main.py fetch 0050 00878 00919 0056 006208

# 批次抓取全市場 ETF (可限制前 N 檔)
python main.py fetch-all --limit 30

# 查看目前資料庫內已收錄的 ETF
python main.py list

# 檢視某檔 ETF 的前 20 大成分股與持股比例
python main.py show 006208

# 跨 ETF 搜尋某檔個股的權重配置
python main.py search 台積電

# 將資料庫全體資料匯出為 CSV 報表
python main.py export --dir data
```

---

## 🤖 GitHub Actions 自動更新設定

本專案已配置好了完整的自動化工作流程 [`.github/workflows/update_etf.yml`](.github/workflows/update_etf.yml)。

### 推送至 GitHub 步驟：
```bash
git init
git add .
git commit -m "feat: initial commit for taiwan etf holdings scraper"
git branch -M main
git remote add origin https://github.com/<您的用戶名>/<您的倉庫名>.git
git push -u origin main
```

### 權限確認：
至 GitHub 倉庫的 **Settings** -> **Actions** -> **General** -> **Workflow permissions**，確認已勾選 **Read and write permissions**，即可讓 GitHub Actions 自動將每天抓取好的資料寫回 GitHub！

