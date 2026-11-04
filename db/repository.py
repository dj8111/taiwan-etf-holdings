from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from .models import ETFFund, ETFHolding
from collectors.base import ETFPayload


class ETFRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_etf_payload(self, payload: ETFPayload) -> int:
        """
        儲存或更新 ETF 基本資訊與當日成分股明細 (Upsert)
        不同日期的資料會完整保留累積，只有同一 ETF 在同一日期的資料會被覆蓋更新
        """
        fund = self.session.query(ETFFund).filter_by(etf_code=payload.etf_code).first()
        if not fund:
            fund = ETFFund(
                etf_code=payload.etf_code,
                name=payload.etf_name,
                issuer=payload.issuer,
                category=payload.category,
            )
            self.session.add(fund)
            self.session.flush()
        else:
            fund.name = payload.etf_name
            fund.issuer = payload.issuer

        # 只刪除「當天、該 ETF」的既有紀錄，其他歷史日期的資料永遠保留！
        self.session.query(ETFHolding).filter(
            ETFHolding.etf_code == payload.etf_code,
            ETFHolding.record_date == payload.record_date,
        ).delete()

        saved_count = 0
        for item in payload.holdings:
            holding = ETFHolding(
                etf_code=payload.etf_code,
                record_date=payload.record_date,
                stock_code=item.stock_code,
                stock_name=item.stock_name,
                shares=item.shares,
                weight=item.weight,
                market_value=item.market_value,
            )
            self.session.add(holding)
            saved_count += 1

        self.session.commit()
        return saved_count

    def get_available_dates(self, etf_code: str) -> List[date]:
        """
        取得特定 ETF 在資料庫中存在哪些歷史日期
        """
        dates = (
            self.session.query(ETFHolding.record_date)
            .filter(ETFHolding.etf_code == etf_code)
            .distinct()
            .order_by(desc(ETFHolding.record_date))
            .all()
        )
        return [d[0] for d in dates]

    def get_latest_holdings(self, etf_code: str, target_date: Optional[date] = None) -> List[ETFHolding]:
        """
        取得特定 ETF 在特定日期（預設最新日期）的持股明細
        """
        if target_date is None:
            target_date = (
                self.session.query(func.max(ETFHolding.record_date))
                .filter(ETFHolding.etf_code == etf_code)
                .scalar()
            )
        if not target_date:
            return []

        return (
            self.session.query(ETFHolding)
            .filter(ETFHolding.etf_code == etf_code, ETFHolding.record_date == target_date)
            .order_by(desc(ETFHolding.weight))
            .all()
        )

    def get_stock_history_in_etf(self, etf_code: str, stock_keyword: str) -> List[Dict[str, Any]]:
        """
        查詢某檔個股在某檔 ETF 中的歷史持股權重與股數變動軌跡
        """
        results = (
            self.session.query(
                ETFHolding.record_date,
                ETFHolding.stock_code,
                ETFHolding.stock_name,
                ETFHolding.weight,
                ETFHolding.shares,
            )
            .filter(
                ETFHolding.etf_code == etf_code,
                (ETFHolding.stock_name.contains(stock_keyword)) | (ETFHolding.stock_code == stock_keyword)
            )
            .order_by(asc(ETFHolding.record_date))
            .all()
        )
        return [
            {
                "record_date": r.record_date.strftime("%Y-%m-%d"),
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "weight": r.weight,
                "shares": r.shares,
            }
            for r in results
        ]

    def compare_etf_dates(self, etf_code: str, date_old: date, date_new: date) -> Dict[str, Any]:
        """
        比對兩個歷史日期間的持股權重增減與成分股進出 (換股分析)
        """
        old_holdings = {h.stock_name: h for h in self.get_latest_holdings(etf_code, date_old)}
        new_holdings = {h.stock_name: h for h in self.get_latest_holdings(etf_code, date_new)}

        all_stocks = set(old_holdings.keys()) | set(new_holdings.keys())
        diffs = []
        added = []
        removed = []

        for stock in all_stocks:
            old_h = old_holdings.get(stock)
            new_h = new_holdings.get(stock)

            if old_h and new_h:
                w_diff = round(new_h.weight - old_h.weight, 2)
                diffs.append({
                    "stock_name": stock,
                    "old_weight": old_h.weight,
                    "new_weight": new_h.weight,
                    "diff": w_diff,
                })
            elif not old_h and new_h:
                added.append({"stock_name": stock, "weight": new_h.weight})
            elif old_h and not new_h:
                removed.append({"stock_name": stock, "weight": old_h.weight})

        # 排序權重變動
        diffs.sort(key=lambda x: abs(x["diff"]), reverse=True)
        return {
            "diffs": diffs,
            "added": added,
            "removed": removed,
        }

    def find_stock_across_etfs(self, stock_keyword: str) -> List[Dict[str, Any]]:
        """
        跨 ETF 查詢最新持股
        """
        subq = (
            self.session.query(
                ETFHolding.etf_code,
                func.max(ETFHolding.record_date).label("max_date")
            )
            .group_by(ETFHolding.etf_code)
            .subquery()
        )

        results = (
            self.session.query(
                ETFHolding.etf_code,
                ETFFund.name.label("etf_name"),
                ETFHolding.record_date,
                ETFHolding.stock_code,
                ETFHolding.stock_name,
                ETFHolding.weight,
                ETFHolding.shares,
            )
            .join(ETFFund, ETFFund.etf_code == ETFHolding.etf_code)
            .join(
                subq,
                (ETFHolding.etf_code == subq.c.etf_code) & (ETFHolding.record_date == subq.c.max_date)
            )
            .filter(
                (ETFHolding.stock_name.contains(stock_keyword)) | (ETFHolding.stock_code == stock_keyword)
            )
            .order_by(desc(ETFHolding.weight))
            .all()
        )

        return [
            {
                "etf_code": r.etf_code,
                "etf_name": r.etf_name,
                "record_date": r.record_date.strftime("%Y-%m-%d"),
                "stock_name": r.stock_name,
                "stock_code": r.stock_code,
                "weight": r.weight,
                "shares": r.shares,
            }
            for r in results
        ]
