from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PriceCandle(Base):
    __tablename__ = "price_candles"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "timestamp_utc", name="uq_price_candle"),
        Index("ix_price_candles_lookup", "symbol", "interval", "timestamp_utc"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="yahoo_finance")
    collected_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rows_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    earliest_timestamp_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_timestamp_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class MarketAnalysisRecord(Base):
    __tablename__ = "market_analyses"
    __table_args__ = (
        Index("ix_market_analyses_lookup", "symbol", "interval", "analyzed_at_utc"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    candle_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analyzed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_price: Mapped[float] = mapped_column(Float, nullable=False)
    ema20: Mapped[float] = mapped_column(Float, nullable=False)
    ema50: Mapped[float] = mapped_column(Float, nullable=False)
    ema200: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi14: Mapped[float] = mapped_column(Float, nullable=False)
    atr14: Mapped[float] = mapped_column(Float, nullable=False)
    atr_percent: Mapped[float] = mapped_column(Float, nullable=False)
    trend: Mapped[str] = mapped_column(String(32), nullable=False)
    market_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    support_levels_json: Mapped[str] = mapped_column(Text, nullable=False)
    resistance_levels_json: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str] = mapped_column(String(128), nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)


class NewsArticleRecord(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("article_hash", name="uq_news_articles_hash"),
        Index("ix_news_articles_published", "published_at_utc"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    article_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="English")
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    collected_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class NewsAnalysisRecord(Base):
    __tablename__ = "news_analyses"
    __table_args__ = (Index("ix_news_analyses_lookup", "symbol", "analyzed_at_utc"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    analyzed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    relevant_article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    high_impact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    drivers_json: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_quality: Mapped[str] = mapped_column(String(32), nullable=False)

class DecisionAnalysisRecord(Base):
    __tablename__ = "decision_analyses"
    __table_args__ = (
        Index("ix_decision_analyses_lookup", "symbol", "interval", "decided_at_utc"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    market_analysis_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    news_analysis_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    market_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    news_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    combined_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    preferred_action: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    alignment: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    data_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    bullish_scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    bearish_scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    neutral_scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    no_trade_reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)

class RiskEvaluationRecord(Base):
    __tablename__ = "risk_evaluations"
    __table_args__ = (
        Index("ix_risk_evaluations_lookup", "symbol", "interval", "evaluated_at_utc"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluated_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    decision_analysis_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    approved: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    account_balance: Mapped[float] = mapped_column(Float, nullable=False)
    risk_percent: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_loss_amount: Mapped[float] = mapped_column(Float, nullable=False)
    daily_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    daily_loss_limit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_risk_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_per_price_unit: Mapped[float] = mapped_column(Float, nullable=False)
    position_units: Mapped[float] = mapped_column(Float, nullable=False)
    notional_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    minutes_to_high_impact_event: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_age_hours: Mapped[float] = mapped_column(Float, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    checks_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
