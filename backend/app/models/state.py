from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel, Field


class Holding(BaseModel):
    ticker: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float


class NewsItem(BaseModel):
    ticker: str
    title: str
    source: str
    url: str
    published_at: datetime
    summary: str


class FundamentalData(BaseModel):
    ticker: str
    price: float
    change_pct: float
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    volume: Optional[int] = None


class PriceMove(BaseModel):
    ticker: str
    change_pct: float
    direction: str
    is_significant: bool


class BriefSection(BaseModel):
    title: str
    body: str
    tickers: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    ticker: str
    type: str
    title: str
    body: str
    triggered_at: datetime
    read: bool = False


class Brief(BaseModel):
    user_id: str
    date: datetime
    headline: str
    portfolio_health: int = Field(ge=0, le=100)
    sections: list[BriefSection] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)


class WatchmanState(TypedDict):
    user_id: str
    portfolio: list[Holding]
    tickers: list[str]
    news_findings: list[NewsItem]
    fundamental_findings: list[FundamentalData]
    sentiment_scores: dict[str, float]
    price_movements: list[PriceMove]
    brief: Optional[Brief]
    alerts: list[Alert]
    generated_at: Optional[datetime]
