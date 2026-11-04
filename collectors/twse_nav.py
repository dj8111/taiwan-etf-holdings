from datetime import datetime, date
from typing import Dict, Any, List, Optional
import requests
from pydantic import BaseModel


class NavItem(BaseModel):
    etf_code: str
    etf_name: str
    record_date: date
    nav: float
    close_price: Optional[float] = None
    premium_discount_pct: Optional[float] = None
    prev_nav: Optional[float] = None


class TWSENavCollector:
    """
    臺灣證券交易所 (TWSE MIS) 全市場 ETF 每日淨值、市價與折溢價採集器
    單次呼叫即可同步全市場 360+ 檔 ETF 的最新淨值資料
    """
    URL = "https://mis.twse.com.tw/stock/data/all_etf.txt"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mis.twse.com.tw/stock/etf_nav.jsp",
        }

    def fetch_all_navs(self) -> Dict[str, NavItem]:
        """
        抓取全市場 ETF 當日最新每單位淨值、收盤市價與折溢價
        回傳: dict, key 為 etf_code, value 為 NavItem
        """
        try:
            resp = requests.get(self.URL, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                print(f"[!] 呼叫證交所 MIS 淨值 API 失敗，HTTP 狀態碼: {resp.status_code}")
                return {}

            data = resp.json()
        except Exception as e:
            print(f"[!] 解析證交所 MIS 淨值資料異常: {e}")
            return {}

        results: Dict[str, NavItem] = {}
        for group in data.get("a1", []):
            for item in group.get("msgArray", []):
                code = item.get("a", "").strip().upper()
                if not code:
                    continue

                name = item.get("b", "").strip()
                date_raw = str(item.get("i", "")).strip()
                try:
                    record_date = datetime.strptime(date_raw, "%Y%m%d").date()
                except (ValueError, TypeError):
                    record_date = date.today()

                try:
                    nav_val = float(item.get("f"))
                except (ValueError, TypeError):
                    continue

                try:
                    price_val = float(item.get("e"))
                except (ValueError, TypeError):
                    price_val = None

                try:
                    diff_val = float(item.get("g"))
                except (ValueError, TypeError):
                    diff_val = None

                try:
                    prev_nav_val = float(item.get("h"))
                except (ValueError, TypeError):
                    prev_nav_val = None

                results[code] = NavItem(
                    etf_code=code,
                    etf_name=name,
                    record_date=record_date,
                    nav=nav_val,
                    close_price=price_val,
                    premium_discount_pct=diff_val,
                    prev_nav=prev_nav_val,
                )

        return results
