"""
Database models and connection setup for ETF holdings using SQLAlchemy.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()


class ETFFund(Base):
    """
    ETF 基本資料表
    """
    __tablename__ = "etf_funds"

    etf_code = Column(String(10), primary_key=True, index=True, doc="ETF 代號，如 0050, 00878")
    name = Column(String(100), nullable=False, doc="ETF 名稱，如 元大台灣50")
    issuer = Column(String(50), nullable=False, index=True, doc="投信發行商，如 元大投信")
    category = Column(String(50), default="國內股票型", doc="分類，如 國內股票型, 高股息, 債券型")
    tracking_index = Column(String(100), nullable=True, doc="追蹤指數")
    currency = Column(String(10), default="TWD", doc="計價幣別")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯到每日持股明細
    holdings = relationship("ETFHolding", back_populates="fund", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ETFFund(code='{self.etf_code}', name='{self.name}', issuer='{self.issuer}')>"


class ETFHolding(Base):
    """
    ETF 每日持股成分股與權重明細表
    """
    __tablename__ = "etf_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    etf_code = Column(String(10), ForeignKey("etf_funds.etf_code", ondelete="CASCADE"), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True, doc="持股基準日期")
    stock_code = Column(String(20), nullable=False, index=True, doc="成分股代號，如 2330")
    stock_name = Column(String(100), nullable=False, doc="成分股名稱，如 台積電")
    shares = Column(Float, nullable=True, doc="持有股數")
    weight = Column(Float, nullable=False, doc="持股權重百分比 (例如 52.35 代表 52.35%)")
    market_value = Column(Float, nullable=True, doc="持股市值金額")
    created_at = Column(DateTime, default=datetime.utcnow)

    fund = relationship("ETFFund", back_populates="holdings")

    # 複合唯一約束：確保同一檔 ETF 在同一個基準日，同一檔成分股只有一筆紀錄
    __table_args__ = (
        UniqueConstraint("etf_code", "record_date", "stock_code", name="uq_etf_date_stock"),
        Index("idx_etf_date", "etf_code", "record_date"),
        Index("idx_stock_date", "stock_code", "record_date"),
    )

    def __repr__(self):
        return (
            f"<ETFHolding(etf='{self.etf_code}', date='{self.record_date}', "
            f"stock='{self.stock_code} {self.stock_name}', weight={self.weight}%)>"
        )


def init_db(db_url: str = "sqlite:///etf_data.db"):
    """
    初始化資料庫連線與自動建立資料表
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return engine, session_factory

