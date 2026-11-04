"""
Taiwan ETF Holdings CLI Manager & Reverse API Scraper
"""

import os
import sys
import time
import argparse
from datetime import date
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
    將資料庫中的全體 ETF 與最新成分股匯出為 CSV 檔案
    """
    os.makedirs(output_dir, exist_ok=True)
    engine, _ = init_db()

    query = """
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
    ORDER BY f.etf_code, h.weight DESC
    """
    df = pd.read_sql(query, engine)
    csv_path = os.path.join(output_dir, "etf_holdings_latest.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 成功匯出 {len(df)} 筆持股紀錄至: {csv_path}")


def list_funds():
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        funds = session.query(ETFFund).all()
        if not funds:
            print("資料庫內目前尚無 ETF 資料，請先執行抓取命令 (例如: python main.py fetch 0050 00878)")
            return

        print(f"\n{'代號':<8} {'名稱':<22} {'投信發行商':<12} {'類別':<14} {'成分股數':<8}")
        print("-" * 70)
        for f in funds:
            holdings_count = len(f.holdings) if f.holdings else 0
            print(f"{f.etf_code:<8} {f.name:<22} {f.issuer:<12} {f.category:<14} {holdings_count:<8}")
        print(f"\n目前資料庫累計已收錄: {len(funds)} 檔 ETF\n")


def show_holdings(etf_code: str, top_n: int = 20):
    engine, SessionFactory = init_db()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        holdings = repo.get_latest_holdings(etf_code)
        if not holdings:
            print(f"查無 {etf_code} 的持股資料。您可以先執行: python main.py fetch {etf_code}")
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
    parser = argparse.ArgumentParser(description="台灣投信 ETF 持股明細抓取與資料庫管理系統")
    subparsers = parser.add_subparsers(dest="command", help="操作子命令")

    # fetch 命令
    fetch_parser = subparsers.add_parser("fetch", help="抓取指定 ETF 並存入資料庫")
    fetch_parser.add_argument("codes", nargs="+", help="ETF 代號 (如 0050 00878 00919 0056)")

    # fetch-all 命令
    fetchall_parser = subparsers.add_parser("fetch-all", help="從證交所自動獲取清單並批次抓取全體 ETF")
    fetchall_parser.add_argument("--limit", type=int, default=None, help="限制抓取前 N 檔 (除錯或快速測試用)")
    fetchall_parser.add_argument("--delay", type=float, default=1.0, help="每檔抓取間隔秒數 (預設 1.0 秒避免被擋)")

    # export 命令
    export_parser = subparsers.add_parser("export", help="將資料庫持股資料匯出為 CSV")
    export_parser.add_argument("--dir", default="data", help="輸出資料夾 (預設 data)")

    # list 命令
    subparsers.add_parser("list", help="列出資料庫現存所有 ETF")

    # show 命令
    show_parser = subparsers.add_parser("show", help="檢視某檔 ETF 的成分股權重")
    show_parser.add_argument("code", help="ETF 代號 (如 00878)")
    show_parser.add_argument("--top", type=int, default=20, help="顯示前 N 大持股 (預設 20)")

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
        show_holdings(args.code, args.top)
    elif args.command == "search":
        search_stock(args.keyword)
    else:
        print("未指定子命令，可用命令:")
        print("  python main.py fetch <代號...>   抓取指定 ETF (如: python main.py fetch 0050 00878)")
        print("  python main.py fetch-all          自動從證交所抓取全體 240+ 檔 ETF")
        print("  python main.py export             匯出資料庫內容為 data/etf_holdings_latest.csv")
        print("  python main.py list               列出目前資料庫內所有 ETF 與檔數")
        print("  python main.py show <代號>        顯示該 ETF 前 20 大持股與比例")
        print("  python main.py search <個股>      跨 ETF 搜尋某檔個股的權重分布")


if __name__ == "__main__":
    main()
