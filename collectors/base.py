from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date
from pydantic import BaseModel


class HoldingItem(BaseModel):
    stock_code: str
    stock_name: str
    shares: Optional[float] = None
    weight: float
    market_value: Optional[float] = None


class ETFPayload(BaseModel):
    etf_code: str
    etf_name: str
    issuer: str
    record_date: date
    holdings: List[HoldingItem]
    category: str = "國內股票型"


class BaseCollector(ABC):
    @abstractmethod
    def fetch_holdings(self, etf_code: str, target_date: Optional[date] = None) -> Optional[ETFPayload]:
        """
        取得特定 ETF 的持股成分股與權重
        """
        pass

