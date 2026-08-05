from datetime import datetime, timedelta, timezone

from app.collectors.news import RawNewsArticle
from app.engines.news_engine import analyze_news, score_article


def article(title: str, hours_old: int = 1, source_type: str = "official_statistics") -> RawNewsArticle:
    return RawNewsArticle(
        title=title,
        url="https://example.com/item",
        published_at_utc=datetime.now(timezone.utc) - timedelta(hours=hours_old),
        source="Test Source",
        source_type=source_type,
        reliability=1.0,
    )


def test_gold_hawkish_yields_is_bearish():
    scored = score_article(article("Fed hawkish as real yields rise and strong dollar pressures gold"), "GC=F")
    assert scored.relevance >= 0.5
    assert scored.impact == "bearish"
    assert scored.category in {"central_bank", "rates_credit", "currency"}


def test_eurusd_fed_cut_is_bullish():
    scored = score_article(article("Fed rate cut sends dollar lower as euro strengthens"), "EURUSD=X")
    assert scored.impact == "bullish"
    assert scored.score > 0


def test_old_news_decays():
    fresh = score_article(article("Fed rate hike and higher yields weigh on gold", 1), "GC=F")
    old = score_article(article("Fed rate hike and higher yields weigh on gold", 60), "GC=F")
    assert abs(fresh.score) > abs(old.score)


def test_duplicate_event_is_capped():
    items = [article("Fed rate cut weakens dollar and supports gold", source_type="global_news_index") for _ in range(8)]
    result = analyze_news(items, "GC=F", use_ollama=False)
    assert result.relevant_article_count <= 2
