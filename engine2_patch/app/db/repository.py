from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import CollectionRun, PriceCandle


def begin_collection_run(session: Session, symbol: str, interval: str, period: str) -> CollectionRun:
    run = CollectionRun(
        symbol=symbol,
        interval=interval,
        period=period,
        started_at_utc=datetime.now(timezone.utc),
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def finish_collection_run(
    session: Session,
    run: CollectionRun,
    *,
    status: str,
    rows_received: int = 0,
    rows_written: int = 0,
    duplicate_rows: int = 0,
    invalid_rows: int = 0,
    earliest_timestamp_utc: datetime | None = None,
    latest_timestamp_utc: datetime | None = None,
    error_message: str | None = None,
) -> None:
    run.completed_at_utc = datetime.now(timezone.utc)
    run.status = status
    run.rows_received = rows_received
    run.rows_written = rows_written
    run.duplicate_rows = duplicate_rows
    run.invalid_rows = invalid_rows
    run.earliest_timestamp_utc = earliest_timestamp_utc
    run.latest_timestamp_utc = latest_timestamp_utc
    run.error_message = error_message
    session.commit()


def upsert_price_candles(session: Session, df: pd.DataFrame, symbol: str, interval: str) -> int:
    if df.empty:
        return 0

    timestamps = [ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts for ts in df.index]
    session.execute(
        delete(PriceCandle).where(
            PriceCandle.symbol == symbol,
            PriceCandle.interval == interval,
            PriceCandle.timestamp_utc.in_(timestamps),
        )
    )

    collected_at = datetime.now(timezone.utc)
    rows = []
    for ts, row in df.iterrows():
        rows.append(
            PriceCandle(
                symbol=symbol,
                interval=interval,
                timestamp_utc=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                adj_close=float(row["Adj Close"]) if "Adj Close" in row and pd.notna(row["Adj Close"]) else None,
                volume=float(row["Volume"]) if "Volume" in row and pd.notna(row["Volume"]) else None,
                source="yahoo_finance",
                collected_at_utc=collected_at,
            )
        )
    session.add_all(rows)
    session.commit()
    return len(rows)


def get_data_summary(session: Session, symbol: str, interval: str) -> dict:
    result = session.execute(
        select(
            func.count(PriceCandle.id),
            func.min(PriceCandle.timestamp_utc),
            func.max(PriceCandle.timestamp_utc),
        ).where(PriceCandle.symbol == symbol, PriceCandle.interval == interval)
    ).one()
    return {"rows": int(result[0] or 0), "earliest": result[1], "latest": result[2]}


def load_price_candles(session: Session, symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
    from app.db.models import PriceCandle

    rows = session.execute(
        select(PriceCandle)
        .where(PriceCandle.symbol == symbol, PriceCandle.interval == interval)
        .order_by(PriceCandle.timestamp_utc.desc())
        .limit(limit)
    ).scalars().all()
    rows.reverse()
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    return pd.DataFrame(
        {
            "Open": [row.open for row in rows],
            "High": [row.high for row in rows],
            "Low": [row.low for row in rows],
            "Close": [row.close for row in rows],
            "Volume": [row.volume for row in rows],
        },
        index=pd.DatetimeIndex([row.timestamp_utc for row in rows], name="timestamp_utc"),
    )


def save_market_analysis(session: Session, analysis) -> int:
    import json
    from datetime import datetime
    from app.db.models import MarketAnalysisRecord

    candle_time = datetime.fromisoformat(analysis.candle_timestamp_utc.replace("Z", "+00:00"))
    record = MarketAnalysisRecord(
        symbol=analysis.symbol,
        interval=analysis.interval,
        candle_timestamp_utc=candle_time,
        last_price=analysis.last_price,
        ema20=analysis.ema20,
        ema50=analysis.ema50,
        ema200=analysis.ema200,
        rsi14=analysis.rsi14,
        atr14=analysis.atr14,
        atr_percent=analysis.atr_percent,
        trend=analysis.trend,
        market_regime=analysis.market_regime,
        bias=analysis.bias,
        confidence=analysis.confidence,
        support_levels_json=json.dumps(analysis.support_levels),
        resistance_levels_json=json.dumps(analysis.resistance_levels),
        invalidation_level=analysis.invalidation_level,
        data_quality=analysis.data_quality,
        reasons_json=json.dumps(analysis.reasons),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return int(record.id)


def upsert_news_articles(session: Session, articles) -> int:
    from app.collectors.news import article_key
    from app.db.models import NewsArticleRecord

    written = 0
    for article in articles:
        key = article_key(article.title, article.url)
        existing = session.execute(select(NewsArticleRecord).where(NewsArticleRecord.article_hash == key)).scalar_one_or_none()
        if existing is None:
            session.add(
                NewsArticleRecord(
                    article_hash=key,
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    source_type=article.source_type,
                    published_at_utc=article.published_at_utc,
                    summary=article.summary,
                    language=article.language,
                    reliability=article.reliability,
                    collected_at_utc=article.collected_at_utc or datetime.now(timezone.utc),
                )
            )
            written += 1
        else:
            existing.title = article.title
            existing.source = article.source
            existing.source_type = article.source_type
            existing.published_at_utc = article.published_at_utc
            existing.summary = article.summary
            existing.language = article.language
            existing.reliability = article.reliability
            existing.collected_at_utc = article.collected_at_utc or datetime.now(timezone.utc)
    session.commit()
    return written


def save_news_analysis(session: Session, analysis) -> int:
    import json
    from app.db.models import NewsAnalysisRecord

    record = NewsAnalysisRecord(
        symbol=analysis.symbol,
        analyzed_at_utc=datetime.fromisoformat(analysis.analyzed_at_utc.replace("Z", "+00:00")),
        article_count=analysis.article_count,
        relevant_article_count=analysis.relevant_article_count,
        source_count=analysis.source_count,
        bias=analysis.bias,
        score=analysis.score,
        confidence=analysis.confidence,
        high_impact_count=analysis.high_impact_count,
        summary=analysis.summary,
        drivers_json=json.dumps([item.__dict__ if hasattr(item, "__dict__") else {
            "title": item.title, "url": item.url, "source": item.source,
            "published_at_utc": item.published_at_utc, "relevance": item.relevance,
            "importance": item.importance, "impact": item.impact, "score": item.score,
            "matched_terms": item.matched_terms, "reliability": item.reliability,
        } for item in analysis.drivers]),
        warnings_json=json.dumps(analysis.warnings),
        model_name=analysis.model_name,
        data_quality=analysis.data_quality,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return int(record.id)
