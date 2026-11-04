# 台灣股市全市場 ETF 持股明細與每日淨值自動採集系統

基於 Python 與 Reverse API 技術，自動抓取台灣全市場（上市 TWSE + 上櫃 TPEx 共 364 檔）ETF 每日每單位淨值、收盤市價、折溢價幅度以及成分股明細、股數與權重比例，並持久化至關聯式資料庫（SQLite / PostgreSQL），透過 GitHub Actions 每日盤後自動排程更新。

---

## 🌟 功能特點

- **全市場 100% 涵蓋**：收錄臺灣證交所（TWSE）與櫃買中心（TPEx）**全體 364 檔 ETF**（股票型、高股息、債券型、海外型、主題型、期貨槓反型）。
- **雙重維度數據**：
  - **每日每單位淨值 (NAV)**：包含最新每單位淨值、收盤價、前日淨值與折溢價幅度（%）。
  - **每日成分股權重**：各檔 ETF 完整成分股清單、持股數與權重比例（%）。
- **永久歷史時間序列**：內建 SQLAlchemy ORM 模型，以 `record_date` 為基準累積歷史，支援任意日期間換股增減比對（`diff`）與個股走勢追蹤（`history`）。
- **多格式同步保存**：自動更新 SQLite 資料庫（`etf_data.db`），並匯出全歷史 CSV（`data/etf_holdings_all_history.csv`、`data/etf_navs_history.csv`）與每日分檔封存（`data/daily/YYYY-MM-DD.csv`）。
- **GitHub Actions 全市場自動化**：每個台股交易日收盤後（週一至週五 18:30 台灣時間）自動啟動【全市場極限模式】，更新 364 檔 ETF 並 Commit 回儲存庫。

---

## 🚀 本地常用操作指令

```bash
# 啟動全市場極限模式 (批次抓取 364 檔每日淨值 + 持股)
python main.py fetch-all

# 抓取全市場 364 檔 ETF 當日最新每單位淨值 (只需 2 秒)
python main.py fetch-nav

# 抓取指定核心 ETF 並入庫 (例如: 0050 00878 00919 00918)
python main.py fetch 0050 00878 00919 00918

# 查看某檔 ETF 歷史每日淨值、市價與折溢價走勢
python main.py nav 0050

# 查看某檔 ETF 最新淨值與前 20 大成分股明細
python main.py show 00878

# 查詢某檔成分股在特定 ETF 的歷史權重走勢
python main.py history 00878 廣達

# 換股分析：比對兩日期的成分股增減與進出名單
python main.py diff 00878 2026-11-04 2026-11-05

# 跨 ETF 搜尋某檔個股的權重配置 (如 台積電、長榮)
python main.py search 台積電

# 匯出最新快照與全歷史 CSV
python main.py export --dir data
```
