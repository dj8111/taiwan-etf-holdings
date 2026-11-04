from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import ETFFund, ETFHolding
from collectors.base import ETFPayload


class ETFRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_etf_payload(self, payload: ETFPayload) -> int:
        """
        儲存或更新 ETF 基本資訊與當日成分股明細 (Upsert)
        回傳成功存入的持股成分檔數
        """
        # 1. 確保 ETF 基本資料存在
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

        # 2. 清除該 ETF 在該基準日期的既有資料 (避免重複鍵衝突)，再整批寫入
        self.session.query(ETFHolding).filter(
            ETFHolding.etf_code == payload.etf_code,
            ETFHolding.record_date == payload.record_date,
        ).delete()

        # 3. 寫入最新成分股
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

    def get_latest_holdings(self, etf_code: str) -> List[ETFHolding]:
        """
        取得特定 ETF 最新的持股明細
        """
        latest_date = (
            self.session.query(func.max(ETFHolding.record_date))
            .filter(ETFHolding.etf_code == etf_code)
            .scalar()
        )
        if not latest_date:
            return []

        return (
            self.session.query(ETFHolding)
            .filter(ETFHolding.etf_code == etf_code, ETFHolding.record_date == latest_date)
            .order_by(desc(ETFHolding.weight))
            .all()
        )

    def find_stock_across_etfs(self, stock_keyword: str) -> List[Dict[str, Any]]:
        """
        查詢某檔個股被哪些 ETF 持有及其權重排名 (例如查詢 '台積電')
        """
        # 取得每檔 ETF 的最新日期子查詢
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

