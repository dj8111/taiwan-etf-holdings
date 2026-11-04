"""
Taiwan ETF Holdings CLI Manager & Reverse API Scraper
"""

import os
import sys
import time
import argparse
from datetime import date, datetime
from typing import List, Optional
import requests
import pandas as pd

from db.models import init_db, ETFFund, ETFHolding
from db.repository import ETFRepository
from collectors.cathay import CathayCollector
from collectors.moneydj import MoneyDJCollector


def get_collectors():
    return {
        "cathay": CathayCollector(),
        "moneydj": MoneyDJCollector(),
    }


def fetch_all_twse_etf_codes() -> List[dict]:
    """
    從臺灣證交所 OpenAPI 取得全體上市 ETF 清單 (約 240+ 檔)
    """
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            etfs = [
                {"code": item.get("Code", "").strip(), "name": item.get("Name", "").strip()}
                for item in data
                if item.get("Code", "").strip().startswith("00")
            ]
            return etfs
    except Exception as e:
        print(f"[!] 呼叫證交所清單失敗: {e}")
    return []


def fetch_and_save(etf_codes: List[str]):
    engine, SessionFactory = init_db()
    collectors = get_collectors()

    with SessionFactory() as session:
        repo = ETFRepository(session)
        print(f"\n=======================================================")
        print(f" 開始抓取各投信 ETF 持股明細與比例，存入資料庫")
        print(f" 目標標的: {', '.join(etf_codes)}")
        print(f"=======================================================\n")

        for code in etf_codes:
            code = code.strip().upper()
            payload = None

            # 1. 優先嘗試官方投信專屬採集器 (例如國泰)
            if code in CathayCollector.FUND_MAP:
                print(f"[*] 嘗試呼叫 [國泰投信官方 API] 取得 {code} ...")
                try:
                    payload = collectors["cathay"].fetch_holdings(code)
                except Exception as e:
                    print(f"    [!] 國泰官方 API 異常 ({e})，準備切換至備援來源...")

            # 2. 若專屬採集器未命中或失敗，使用通用採集器 (MoneyDJ)
            if not payload:
                print(f"[*] 嘗試透過 [MoneyDJ 數據端點] 取得 {code} ...")
                try:
                    payload = collectors["moneydj"].fetch_holdings(code)
                except Exception as e:
                    print(f"    [!] 抓取 {code} 發生錯誤: {e}")
                    continue

            if payload and payload.holdings:
                count = repo.save_etf_payload(payload)
                print(f"    [OK] 成功更新: {payload.etf_code} {payload.etf_name} (發行商: {payload.issuer})")
                print(f"         基準日期: {payload.record_date} | 成分股檔數: {count} 檔\n")
            else:
                print(f"    [X] 未能取得 {code} 的持股明細資料。\n")


def fetch_all_batch(limit: Optional[int] = None, delay: float = 1.0):
    """
    批次抓取全台灣所有上市 ETF
    """
    print("[*] 正在從臺灣證券交易所 OpenAPI 取得全體 ETF 列表...")
    etfs = fetch_all_twse_etf_codes()
    if not etfs:
        print("[!] 無法取得證交所列表。")
        return

    total = len(etfs)
    target_etfs = etfs[:limit] if limit else etfs
    print(f"[*] 證交所共發現 {total} 檔 ETF。本次預計抓取 {len(target_etfs)} 檔。\n")

    codes = [e["code"] for e in target_etfs]
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{len(codes)}] 處理 {code} ...")
        fetch_and_save([code])
        if delay > 0 and i < len(codes):
            time.sleep(delay)


def export_csv(output_dir: str = "data"):
    """
    將資料庫持股資料匯出為 CSV 報表：
    1. etf_holdings_latest.csv (每檔 ETF 最新一筆)
    2. etf_holdings_all_history.csv (全歷史累積紀錄)
    3. daily/YYYY-MM-DD.csv (當日封存快照)
    """
    os.makedirs(output_dir, exist_ok=True)
    daily_dir = os.path.join(output_dir, "daily")
    os.makedirs(daily_dir, exist_ok=True)

    engine, _ = init_db()

    # 1. 匯出全歷史紀錄
    query_all = """
    SELECT 
        f.etf_code,
        f.name AS etf_name,
        f.issuer,
        f.category,
        h.record_date,
        h.stock_code,
        h.stock_name,
        h.weight,
        h.shares
    FROM etf_holdings h
    JOIN etf_funds f ON h.etf_code = f.etf_code
    ORDER BY f.etf_code, h.record_date DESC, h.weight DESC
    """
    df_all = pd.read_sql(query_all, engine)
    all_csv_path = os.path.join(output_dir, "etf_holdings_all_history.csv")
    df_all.to_csv(all_csv_path, index=False, encoding="utf-8-sig")

    # 2. 匯出最新單日快照
    subq_latest = """
    SELECT h.*, f.name AS etf_name, f.issuer, f.category
    FROM etf_holdings h
    JOIN etf_funds f ON h.etf_code = f.etf_code
    JOIN (
        SELECT etf_code, MAX(record_date) as max_date
        FROM etf_holdings
        GROUP BY etf_code
    ) latest ON h.etf_code = latest.etf_code AND h.record_date = latest.max_date
    ORDER BY h.etf_code, h.weight DESC
    """
    df_latest = pd.read_sql(subq_latest, engine)
    latest_csv_path = os.path.join(output_dir, "etf_holdings_latest.csv")
    df_latest.to_csv(latest_csv_path, index=False, encoding="utf-8-sig")

    # 3. 按日期分別歸檔到 daily/
    today_str = date.today().strftime("%Y-%m-%d")
    daily_csv_path = os.path.join(daily_dir, f"{today_str}.csv")
    df_latest.to_csv(daily_csv_path, index=False, encoding="utf-8-sig")

    print(f"[OK] 歷史總表匯出完成 ({len(df_all)} 筆): {all_csv_path}")
    print(f"[OK] 最新快照匯出完成 ({len(df_latest)} 筆): {latest_csv_path}")
    print(f"[OK] 今日快照封存完成: {daily_csv_path}")


def list_funds():
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        funds = session.query(ETFFund).all()
        if not funds:
            print("資料庫內目前尚無 ETF 資料，請先執行抓取命令 (例如: python main.py fetch 0050 00878)")
            return

        print(f"\n{'代號':<8} {'名稱':<22} {'投信發行商':<12} {'類別':<14} {'歷史紀錄數':<8}")
        print("-" * 72)
        for f in funds:
            holdings_count = len(f.holdings) if f.holdings else 0
            print(f"{f.etf_code:<8} {f.name:<22} {f.issuer:<12} {f.category:<14} {holdings_count:<8}")
        print(f"\n目前資料庫累計已收錄: {len(funds)} 檔 ETF\n")


def show_holdings(etf_code: str, target_date_str: Optional[str] = None, top_n: int = 20):
    engine, SessionFactory = init_db()
    target_d = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else None

    with SessionFactory() as session:
        repo = ETFRepository(session)
        holdings = repo.get_latest_holdings(etf_code, target_d)
        if not holdings:
            print(f"查無 {etf_code} {'在 ' + target_date_str if target_date_str else ''} 的持股資料。")
            return

        fund = session.query(ETFFund).filter_by(etf_code=etf_code).first()
        fund_name = fund.name if fund else etf_code
        issuer = fund.issuer if fund else "未知"
        record_date = holdings[0].record_date

        print(f"\n=======================================================")
        print(f" [{etf_code}] {fund_name} ({issuer}) - 持股明細")
        print(f" 基準日: {record_date} | 總成分股: {len(holdings)} 檔 | 前 {min(top_n, len(holdings))} 大權重")
        print(f"=======================================================")
        print(f"{'排名':<6} {'代號/名稱':<18} {'持股比例(%)':<12} {'持有股數':<15}")
        print("-" * 55)
        for idx, h in enumerate(holdings[:top_n], 1):
            shares_str = f"{int(h.shares):,}" if h.shares else "N/A"
            stock_display = f"{h.stock_code} {h.stock_name}" if h.stock_code != h.stock_name else h.stock_name
            print(f"{idx:<6} {stock_display:<18} {h.weight:>8.2f}%   {shares_str:>15}")
        print()


def show_stock_history(etf_code: str, stock_name: str):
    """
    顯示某檔成分股在特定 ETF 的歷史權重與股數變化走勢
    """
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        history = repo.get_stock_history_in_etf(etf_code, stock_name)
        if not history:
            print(f"在 {etf_code} 中查無 「{stock_name}」 的歷史資料。")
            return

        print(f"\n=======================================================")
        print(f" [{etf_code}] 成分股歷史權重追蹤: 「{stock_name}」")
        print(f"=======================================================")
        print(f"{'日期':<14} {'股票代號/名稱':<16} {'權重比例(%)':<12} {'持有股數':<15}")
        print("-" * 60)
        for h in history:
            shares_str = f"{int(h['shares']):,}" if h['shares'] else "N/A"
            print(f"{h['record_date']:<14} {h['stock_name']:<16} {h['weight']:>8.2f}%   {shares_str:>15}")
        print()


def show_diff(etf_code: str, date1_str: str, date2_str: str):
    """
    比對兩日期的成分股增減與換股分析
    """
    d1 = datetime.strptime(date1_str, "%Y-%m-%d").date()
    d2 = datetime.strptime(date2_str, "%Y-%m-%d").date()

    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        result = repo.compare_etf_dates(etf_code, d1, d2)

        print(f"\n=======================================================")
        print(f" [{etf_code}] 歷史換股與權重增減比對: {date1_str} -> {date2_str}")
        print(f"=======================================================")

        if result["added"]:
            print(f"\n[+] 新增成分股 ({len(result['added'])} 檔):")
            for item in result["added"]:
                print(f"    + {item['stock_name']:<12} (新權重: {item['weight']:.2f}%)")

        if result["removed"]:
            print(f"\n[-] 剔除成分股 ({len(result['removed'])} 檔):")
            for item in result["removed"]:
                print(f"    - {item['stock_name']:<12} (原權重: {item['weight']:.2f}%)")

        print(f"\n[=] 持股權重增減變化 (前 15 大變動):")
        print(f"{'成分股':<14} {'原權重':<10} {'新權重':<10} {'變動(%)':<10}")
        print("-" * 50)
        for d in result["diffs"][:15]:
            sign = "+" if d["diff"] > 0 else ""
            print(f"{d['stock_name']:<14} {d['old_weight']:>6.2f}%    {d['new_weight']:>6.2f}%    {sign}{d['diff']:>6.2f}%")
        print()


def list_dates(etf_code: str):
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        dates = repo.get_available_dates(etf_code)
        if not dates:
            print(f"資料庫查無 {etf_code} 的歷史紀錄。")
            return
        print(f"\n[{etf_code}] 資料庫現有歷史基準日 ({len(dates)} 天):")
        for d in dates:
            print(f"  - {d.strftime('%Y-%m-%d')}")
        print()


def search_stock(keyword: str):
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        results = repo.find_stock_across_etfs(keyword)
        if not results:
            print(f"在各 ETF 持股中未搜尋到與「{keyword}」相關的成分股。")
            return

        print(f"\n=======================================================")
        print(f" 跨 ETF 搜尋持股: 「{keyword}」")
        print(f"=======================================================")
        print(f"{'ETF代號':<8} {'ETF名稱':<20} {'基準日':<12} {'成分股':<12} {'權重(%)':<10}")
        print("-" * 68)
        for r in results:
            print(f"{r['etf_code']:<8} {r['etf_name']:<20} {r['record_date']:<12} {r['stock_name']:<12} {r['weight']:>6.2f}%")
        print()


def main():
    parser = argparse.ArgumentParser(description="台灣投信 ETF 持股明細抓取與歷史資料庫管理系統")
    subparsers = parser.add_subparsers(dest="command", help="操作子命令")

    # fetch 命令
    fetch_parser = subparsers.add_parser("fetch", help="抓取指定 ETF 並存入資料庫")
    fetch_parser.add_argument("codes", nargs="+", help="ETF 代號 (如 0050 00878 00919 0056)")

    # fetch-all 命令
    fetchall_parser = subparsers.add_parser("fetch-all", help="從證交所自動獲取清單並批次抓取全體 ETF")
    fetchall_parser.add_argument("--limit", type=int, default=None, help="限制抓取前 N 檔")
    fetchall_parser.add_argument("--delay", type=float, default=1.0, help="每檔抓取間隔秒數")

    # export 命令
    export_parser = subparsers.add_parser("export", help="將資料庫全歷史與最新持股匯出為 CSV")
    export_parser.add_argument("--dir", default="data", help="輸出資料夾 (預設 data)")

    # list 命令
    subparsers.add_parser("list", help="列出資料庫現存所有 ETF")

    # show 命令
    show_parser = subparsers.add_parser("show", help="檢視某檔 ETF 的成分股權重")
    show_parser.add_argument("code", help="ETF 代號 (如 00878)")
    show_parser.add_argument("--date", default=None, help="指定查詢特定歷史日期 (YYYY-MM-DD)")
    show_parser.add_argument("--top", type=int, default=20, help="顯示前 N 大持股")

    # history 命令
    hist_parser = subparsers.add_parser("history", help="查詢某檔成分股在特定 ETF 的歷史權重軌跡")
    hist_parser.add_argument("code", help="ETF 代號 (如 00878)")
    hist_parser.add_argument("stock", help="成分股名稱 (如 廣達 或 聯發科)")

    # diff 命令
    diff_parser = subparsers.add_parser("diff", help="比對兩日期的成分股增減與換股分析")
    diff_parser.add_argument("code", help="ETF 代號 (如 00878)")
    diff_parser.add_argument("date1", help="舊日期 (YYYY-MM-DD)")
    diff_parser.add_argument("date2", help="新日期 (YYYY-MM-DD)")

    # dates 命令
    dates_parser = subparsers.add_parser("dates", help="列出某檔 ETF 資料庫內的所有歷史日期")
    dates_parser.add_argument("code", help="ETF 代號 (如 00878)")

    # search 命令
    search_parser = subparsers.add_parser("search", help="跨 ETF 搜尋某檔個股的權重配置")
    search_parser.add_argument("keyword", help="股票名稱或代號 (如 台積電 或 聯發科)")

    args = parser.parse_args()

    if args.command == "fetch":
        fetch_and_save(args.codes)
    elif args.command == "fetch-all":
        fetch_all_batch(limit=args.limit, delay=args.delay)
    elif args.command == "export":
        export_csv(args.dir)
    elif args.command == "list":
        list_funds()
    elif args.command == "show":
        show_holdings(args.code, args.date, args.top)
    elif args.command == "history":
        show_stock_history(args.code, args.stock)
    elif args.command == "diff":
        show_diff(args.code, args.date1, args.date2)
    elif args.command == "dates":
        list_dates(args.code)
    elif args.command == "search":
        search_stock(args.keyword)
    else:
        print("未指定子命令，可用命令:")
        print("  python main.py fetch <代號...>              抓取指定 ETF")
        print("  python main.py show <代號> [--date YYYY-MM-DD] 檢視指定歷史日期的持股")
        print("  python main.py dates <代號>                 查看該 ETF 累積了哪些歷史日期")
        print("  python main.py history <ETF代號> <個股>      查詢某檔個股在此 ETF 的歷史權重走勢")
        print("  python main.py diff <ETF代號> <日期1> <日期2> 換股分析（比對兩日期的增減與新增/剔除）")
        print("  python main.py search <個股>                 跨 ETF 搜尋個股分布")
        print("  python main.py export                       匯出最新與全歷史 CSV 報表")


if __name__ == "__main__":
    main()
