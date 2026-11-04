import io
import re
from datetime import date, datetime
from typing import Optional, Dict
import requests
import pandas as pd

from .base import BaseCollector, ETFPayload, HoldingItem


class CathayCollector(BaseCollector):
    """
    國泰投信官方 API 採集器
    端點: https://cwapi.cathaysite.com.tw/api/ETF/DownloadETFWeightExcel
    """
    BASE_URL = "https://cwapi.cathaysite.com.tw/api/ETF/DownloadETFWeightExcel"

    # 國泰內部 FundCode 對照表
    FUND_MAP = {
        "00878": "CN",  # 國泰永續高股息
    }

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_holdings(self, etf_code: str, target_date: Optional[date] = None) -> Optional[ETFPayload]:
        fund_internal_code = self.FUND_MAP.get(etf_code)
        if not fund_internal_code:
            return None

        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime("%Y/%m/%d")
        url = f"{self.BASE_URL}?FundCode={fund_internal_code}&SearchDate={date_str}"

        resp = requests.get(url, headers=self.headers, timeout=15)
        if resp.status_code != 200 or len(resp.content) < 100:
            return None

        # 解析 Excel
        df = pd.read_excel(io.BytesIO(resp.content), header=None)

        # 擷取 ETF 名稱與日期
        title_text = str(df.iloc[0, 0])
        # 尋找實際持股表格開始列 (股票代號、股票名稱、股數、持股權重)
        stock_start_idx = None
        for r_idx in range(len(df)):
            row_vals = [str(x).strip() for x in df.iloc[r_idx].dropna()]
            if "股票代號" in row_vals and "股票名稱" in row_vals:
                stock_start_idx = r_idx + 1
                break

        if stock_start_idx is None:
            return None

        holdings = []
        for r in range(stock_start_idx, len(df)):
            row = df.iloc[r]
            code = str(row[0]).strip() if pd.notna(row[0]) else ""
            name = str(row[1]).strip() if pd.notna(row[1]) else ""
            shares_str = str(row[2]).replace(",", "").strip() if pd.notna(row[2]) else "0"
            weight_str = str(row[3]).replace("%", "").strip() if pd.notna(row[3]) else "0"

            if not code or not name or code in ["項目", "債券", "基金代號", "現金"]:
                break

            try:
                shares = float(shares_str)
            except ValueError:
                shares = 0.0

            try:
                weight = float(weight_str)
            except ValueError:
                weight = 0.0

            holdings.append(
                HoldingItem(
                    stock_code=code,
                    stock_name=name,
                    shares=shares,
                    weight=weight,
                )
            )

        return ETFPayload(
            etf_code=etf_code,
            etf_name="國泰永續高股息" if etf_code == "00878" else f"國泰{etf_code}",
            issuer="國泰投信",
            record_date=target_date,
            holdings=holdings,
            category="國內高股息型",
        )

