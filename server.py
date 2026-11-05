"""
FastAPI Server for Taiwan ETF Dashboard
Provides RESTful APIs and serves the frontend Web application.
"""

import os
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, desc, asc

from db.models import init_db, ETFFund, ETFHolding, ETFNav
from db.repository import ETFRepository
from github_sync import sync_from_github, get_sync_status, get_remote_commit_info

# 初始化資料庫連線與動態工廠
engine, SessionFactory = init_db()

def get_session():
    return SessionFactory()

def reload_db():
    global engine, SessionFactory
    if engine:
        engine.dispose()
    engine, SessionFactory = init_db()

app = FastAPI(
    title="台灣股市 ETF 持股與淨值查詢系統",
    description="提供全市場 ETF 最新及歷史持股明細、每日每單位淨值、折溢價及走勢圖 API",
    version="1.0.0",
)

# 支援跨來源存取 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/stats")
def get_stats():
    """
    取得全市場資料庫概況統計
    """
    with SessionFactory() as session:
        total_funds = session.query(ETFFund).count()
        total_holdings = session.query(ETFHolding).count()
        total_navs = session.query(ETFNav).count()
        
        # 有持股資料的 ETF 檔數
        funds_with_holdings = (
            session.query(func.count(func.distinct(ETFHolding.etf_code))).scalar() or 0
        )
        # 有淨值資料的 ETF 檔數
        funds_with_nav = (
            session.query(func.count(func.distinct(ETFNav.etf_code))).scalar() or 0
        )
        
        # 最新淨值日期
        latest_nav_date = session.query(func.max(ETFNav.record_date)).scalar()
        # 最新持股日期
        latest_holding_date = session.query(func.max(ETFHolding.record_date)).scalar()

        return {
            "total_funds": total_funds,
            "funds_with_holdings": funds_with_holdings,
            "funds_with_nav": funds_with_nav,
            "total_holdings_records": total_holdings,
            "total_nav_records": total_navs,
            "latest_nav_date": latest_nav_date.strftime("%Y-%m-%d") if latest_nav_date else None,
            "latest_holding_date": latest_holding_date.strftime("%Y-%m-%d") if latest_holding_date else None,
        }


@app.get("/api/github/status")
def get_github_status_api():
    """
    取得 GitHub 遠端儲存庫與本地數據同步狀態
    """
    sync_status = get_sync_status()
    remote_info = get_remote_commit_info()

    return {
        "repo_name": "dj8111/taiwan-etf-holdings",
        "repo_url": "https://github.com/dj8111/taiwan-etf-holdings",
        "last_sync_time": sync_status.get("last_sync_time"),
        "current_sha": sync_status.get("last_commit_sha", "main"),
        "remote_sha": remote_info.get("sha") if remote_info.get("success") else None,
        "remote_commit_date": remote_info.get("commit_date"),
        "remote_message": remote_info.get("message"),
        "has_update": (
            remote_info.get("success") and 
            remote_info.get("sha") != sync_status.get("last_commit_sha")
        )
    }


@app.post("/api/github/sync")
@app.get("/api/github/sync")
def trigger_github_sync(force: bool = False):
    """
    手動或自動觸發自 GitHub 遠端儲存庫同步最新 etf_data.db 與報表
    """
    def dispose():
        global engine
        if engine:
            engine.dispose()

    result = sync_from_github(dispose_callback=dispose, force=force)
    # 同步完成後重新載入資料庫連線
    reload_db()
    return result


@app.get("/api/etfs")
def get_etf_list(query: Optional[str] = None):
    """
    取得所有 ETF 清單，包含最新淨值與持股概要
    支援 query 關鍵字過濾（代號或名稱）
    """
    with SessionFactory() as session:
        q = session.query(ETFFund)
        if query:
            q = q.filter((ETFFund.etf_code.contains(query)) | (ETFFund.name.contains(query)))
        
        funds = q.order_by(asc(ETFFund.etf_code)).all()

        # 批次查詢最新淨值
        subq_nav = (
            session.query(ETFNav.etf_code, func.max(ETFNav.record_date).label("max_date"))
            .group_by(ETFNav.etf_code)
            .subquery()
        )
        latest_navs = (
            session.query(ETFNav)
            .join(subq_nav, (ETFNav.etf_code == subq_nav.c.etf_code) & (ETFNav.record_date == subq_nav.c.max_date))
            .all()
        )
        nav_map = {n.etf_code: n for n in latest_navs}

        # 批次查詢有持股記錄的 ETF 代號
        holding_codes = set(
            c[0] for c in session.query(ETFHolding.etf_code).distinct().all()
        )

        result = []
        for f in funds:
            nav_item = nav_map.get(f.etf_code)
            result.append({
                "etf_code": f.etf_code,
                "name": f.name,
                "issuer": f.issuer,
                "category": f.category,
                "has_holdings": f.etf_code in holding_codes,
                "nav": nav_item.nav if nav_item else None,
                "close_price": nav_item.close_price if nav_item else None,
                "premium_discount_pct": nav_item.premium_discount_pct if nav_item else None,
                "record_date": nav_item.record_date.strftime("%Y-%m-%d") if nav_item else None,
            })
        return result


@app.get("/api/etf/{code}/summary")
def get_etf_summary(code: str):
    """
    取得指定 ETF 的詳細指標摘要
    """
    code = code.upper()
    with SessionFactory() as session:
        fund = session.query(ETFFund).filter_by(etf_code=code).first()
        if not fund:
            raise HTTPException(status_code=404, detail=f"找不到 ETF: {code}")

        repo = ETFRepository(session)
        latest_nav = repo.get_latest_nav(code)
        available_dates = repo.get_available_dates(code)
        latest_holdings_count = 0
        latest_holding_date = None

        if available_dates:
            latest_holding_date = available_dates[0]
            latest_holdings_count = (
                session.query(ETFHolding)
                .filter(ETFHolding.etf_code == code, ETFHolding.record_date == latest_holding_date)
                .count()
            )

        return {
            "etf_code": fund.etf_code,
            "name": fund.name,
            "issuer": fund.issuer,
            "category": fund.category,
            "currency": fund.currency,
            "latest_nav": {
                "nav": latest_nav.nav if latest_nav else None,
                "close_price": latest_nav.close_price if latest_nav else None,
                "premium_discount_pct": latest_nav.premium_discount_pct if latest_nav else None,
                "prev_nav": latest_nav.prev_nav if latest_nav else None,
                "record_date": latest_nav.record_date.strftime("%Y-%m-%d") if latest_nav else None,
            } if latest_nav else None,
            "holdings_summary": {
                "latest_date": latest_holding_date.strftime("%Y-%m-%d") if latest_holding_date else None,
                "count": latest_holdings_count,
                "available_dates_count": len(available_dates),
            }
        }


@app.get("/api/etf/{code}/nav_history")
def get_etf_nav_history(code: str, limit: int = Query(180, ge=1, le=1000)):
    """
    取得指定 ETF 的歷史每單位淨值、收盤市價、折溢價走勢 (按日期升冪排序)
    """
    code = code.upper()
    with SessionFactory() as session:
        navs = (
            session.query(ETFNav)
            .filter(ETFNav.etf_code == code)
            .order_by(desc(ETFNav.record_date))
            .limit(limit)
            .all()
        )
        # 轉為由舊到新排序供圖表繪製
        navs.reverse()

        return [
            {
                "record_date": n.record_date.strftime("%Y-%m-%d"),
                "nav": n.nav,
                "close_price": n.close_price,
                "premium_discount_pct": n.premium_discount_pct,
                "prev_nav": n.prev_nav,
            }
            for n in navs
        ]


@app.get("/api/etf/{code}/dates")
def get_etf_dates(code: str):
    """
    取得特定 ETF 存在持股紀錄的所有歷史日期清單
    """
    code = code.upper()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        dates = repo.get_available_dates(code)
        return [d.strftime("%Y-%m-%d") for d in dates]


@app.get("/api/etf/{code}/holdings")
def get_etf_holdings(code: str, date_str: Optional[str] = Query(None, alias="date")):
    """
    取得指定 ETF 在指定日期的成分股權重與股數清單 (預設為最新日期)
    包含前後期歷史更新日期資訊
    """
    code = code.upper()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        
        all_dates = repo.get_available_dates(code)
        date_strs = [d.strftime("%Y-%m-%d") for d in all_dates]
        
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式必須為 YYYY-MM-DD")
            # 如果傳入的 date 在該 ETF 中不存在，自動 fallback 回該 ETF 最新日期
            if all_dates and target_date not in all_dates:
                target_date = all_dates[0]
        elif all_dates:
            target_date = all_dates[0]

        holdings = repo.get_latest_holdings(code, target_date=target_date)
        actual_date = holdings[0].record_date.strftime("%Y-%m-%d") if holdings else (date_str or None)

        is_latest = (actual_date == date_strs[0]) if (actual_date and date_strs) else True
        prev_date = None
        next_date = None

        if actual_date and actual_date in date_strs:
            idx = date_strs.index(actual_date)
            # date_strs 依新到舊排序 (index 0 為最新)
            if idx + 1 < len(date_strs):
                prev_date = date_strs[idx + 1]  # 該期更前一次歷史更新日期
            if idx > 0:
                next_date = date_strs[idx - 1]  # 較新的下一期更新日期

        total_weight = sum(h.weight for h in holdings)

        return {
            "etf_code": code,
            "record_date": actual_date,
            "is_latest": is_latest,
            "latest_date": date_strs[0] if date_strs else actual_date,
            "previous_date": prev_date,
            "next_date": next_date,
            "available_dates": date_strs,
            "total_count": len(holdings),
            "total_weight": round(total_weight, 2),
            "holdings": [
                {
                    "stock_code": h.stock_code,
                    "stock_name": h.stock_name,
                    "weight": round(h.weight, 4),
                    "shares": h.shares,
                    "market_value": h.market_value,
                }
                for h in holdings
            ]
        }


@app.get("/api/etf/{code}/stock_history")
def get_stock_history_in_etf(code: str, stock: str = Query(..., min_length=1)):
    """
    查詢特定成分股在該 ETF 的歷史權重與持有股數走勢軌跡
    """
    code = code.upper()
    with SessionFactory() as session:
        repo = ETFRepository(session)
        history = repo.get_stock_history_in_etf(code, stock)
        return history


@app.get("/api/etf/{code}/diff")
def compare_etf_holdings_diff(
    code: str,
    date_old: str = Query(..., description="舊日期 YYYY-MM-DD"),
    date_new: str = Query(..., description="新日期 YYYY-MM-DD")
):
    """
    成分股換股分析：比對兩個歷史日期间的權重增減、新納入與剔除成分股
    """
    code = code.upper()
    try:
        d_old = datetime.strptime(date_old, "%Y-%m-%d").date()
        d_new = datetime.strptime(date_new, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式必須為 YYYY-MM-DD")

    with SessionFactory() as session:
        repo = ETFRepository(session)
        diff_result = repo.compare_etf_dates(code, d_old, d_new)
        return {
            "etf_code": code,
            "date_old": date_old,
            "date_new": date_new,
            **diff_result
        }


@app.get("/api/search/stock")
def search_stock_across_etfs(keyword: str = Query(..., min_length=1)):
    """
    跨 ETF 追蹤個股：查詢市場上哪些 ETF 持有該成分股及各自權重
    """
    with SessionFactory() as session:
        repo = ETFRepository(session)
        results = repo.find_stock_across_etfs(keyword)
        return results


# 掛載靜態網頁與首頁路由
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
os.makedirs(web_dir, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(web_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>ETF Dashboard Web</h1><p>請先建立 web/index.html 檔案</p>")

if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    啟動 FastAPI 伺服器
    """
    import uvicorn
    print(f"\n=======================================================")
    print(f" 🚀 台灣 ETF 持股與淨值查詢系統 已啟動！")
    print(f" 🌐 請在瀏覽器開啟: http://localhost:{port}")
    print(f" 📖 API 互動文件: http://localhost:{port}/docs")
    print(f"=======================================================\n")
    uvicorn.run("server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()

