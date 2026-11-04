import io
import re
from datetime import date, datetime
from typing import Optional, Dict
import requests
import pandas as pd
from bs4 import BeautifulSoup

from .base import BaseCollector, ETFPayload, HoldingItem


class MoneyDJCollector(BaseCollector):
    """
    MoneyDJ 整合型台股 ETF 成分股採集器
    動態支援台灣證券市場全體國內 ETF (如 0050, 0056, 00878, 00919, 00929, 006208, 00713, 00692 等)
    """
    BASE_URL = "https://www.moneydj.com/ETF/X/Basic/Basic0007a.xdjhtm"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_holdings(self, etf_code: str, target_date: Optional[date] = None) -> Optional[ETFPayload]:
        url = f"{self.BASE_URL}?etfid={etf_code}.TW"
        resp = requests.get(url, headers=self.headers, timeout=15)
        if resp.status_code != 200:
            return None

        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. 動態擷取 ETF 名稱
        raw_title = soup.title.get_text(strip=True) if soup.title else f"ETF-{etf_code}"
        # 移除 title 中多餘後綴，如 -MoneyDJ 或 (0050.TW)
        clean_title = re.sub(r"[〈\(（].*?[〉\)）]|-.*$", "", raw_title).strip() or f"ETF-{etf_code}"

        # 2. 動態擷取發行投信名稱 (例如 富邦投信, 元大投信, 國泰投信)
        issuers = re.findall(r"([\u4e00-\u9fa5]{2,4}投信)", resp.text)
        issuer_name = issuers[0] if issuers else "國內投信"

        # 3. 擷取持股資料日期
        date_match = re.search(r"資料日期[：:]\s*(\d{4}/\d{1,2}/\d{1,2})", resp.text)
        record_date = (
            datetime.strptime(date_match.group(1), "%Y/%m/%d").date()
            if date_match
            else (target_date or date.today())
        )

        # 4. 解析持股成分股表格
        all_holdings = []
        for tbl in soup.find_all("table"):
            tbl_text = tbl.get_text()
            if "股票名稱" in tbl_text and "持股" in tbl_text:
                dfs = pd.read_html(io.StringIO(str(tbl)))
                if not dfs:
                    continue
                df = dfs[0]
                for _, row in df.iterrows():
                    name = str(row.get("股票名稱", "")).strip()
                    weight_val = str(row.get("比例", "")).replace("%", "").strip()
                    shares_val = str(row.get("持股(千股)", "")).replace(",", "").strip()

                    if name and name not in ["nan", "股票名稱", "None"]:
                        try:
                            weight = float(weight_val)
                        except ValueError:
                            weight = 0.0
                        try:
                            shares = float(shares_val) * 1000.0  # 單位千股換算成股數
                        except ValueError:
                            shares = None

                        all_holdings.append(
                            HoldingItem(
                                stock_code=name,
                                stock_name=name,
                                shares=shares,
                                weight=weight,
                            )
                        )

        if not all_holdings:
            return None

        # 判斷大致類別
        category = "國內股票型"
        if "高股息" in clean_title or "高息" in clean_title:
            category = "高股息型"
        elif "債" in clean_title:
            category = "債券型"
        elif "科技" in clean_title or "半導體" in clean_title:
            category = "科技/主題型"

        return ETFPayload(
            etf_code=etf_code,
            etf_name=clean_title,
            issuer=issuer_name,
            record_date=record_date,
            holdings=all_holdings,
            category=category,
        )
