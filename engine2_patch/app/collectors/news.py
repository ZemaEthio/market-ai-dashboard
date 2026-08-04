from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlsplit, urlunsplit

import requests

USER_AGENT = "MarketAI-Research/1.0 (+local decision-support project)"

RSS_FEEDS = [
    {
        "source": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "source_type": "official_central_bank",
        "reliability": 1.0,
    },
    {
        "source": "Federal Reserve Speeches",
        "url": "https://www.federalreserve.gov/feeds/speeches.xml",
        "source_type": "official_central_bank",
        "reliability": 1.0,
    },
    {
        "source": "European Central Bank",
        "url": "https://www.ecb.europa.eu/rss/press.html",
        "source_type": "official_central_bank",
        "reliability": 1.0,
    },
    {
        "source": "ECB Speeches",
        "url": "https://www.ecb.europa.eu/rss/speeches.html",
        "source_type": "official_central_bank",
        "reliability": 1.0,
    },
    {
        "source": "Bank of England",
        "url": "https://www.bankofengland.co.uk/rss/news",
        "source_type": "official_central_bank",
        "reliability": 1.0,
    },
]


@dataclass(slots=True)
class RawNewsArticle:
    title: str
    url: str
    published_at_utc: datetime
    source: str
    source_type: str
    summary: str = ""
    language: str = "English"
    reliability: float = 0.7
    collected_at_utc: datetime | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["published_at_utc"] = self.published_at_utc.isoformat()
        payload["collected_at_utc"] = (self.collected_at_utc or datetime.now(timezone.utc)).isoformat()
        return payload


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).strip()
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def article_key(title: str, url: str) -> str:
    normalized_title = re.sub(r"\W+", " ", title.lower()).strip()
    canonical_url = canonicalize_url(url)
    return hashlib.sha256(f"{canonical_url}|{normalized_title}".encode("utf-8")).hexdigest()


def fetch_rss(max_per_feed: int = 40, timeout: int = 20) -> list[RawNewsArticle]:
    import feedparser
    articles: list[RawNewsArticle] = []
    headers = {"User-Agent": USER_AGENT}
    for feed_meta in RSS_FEEDS:
        try:
            response = requests.get(feed_meta["url"], headers=headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception:
            feed = feedparser.parse(feed_meta["url"])
        for entry in feed.entries[:max_per_feed]:
            title = str(entry.get("title", "")).strip()
            if not title:
                continue
            articles.append(
                RawNewsArticle(
                    title=title,
                    url=canonicalize_url(str(entry.get("link", ""))),
                    published_at_utc=_parse_datetime(entry.get("published") or entry.get("updated")),
                    source=feed_meta["source"],
                    source_type=feed_meta["source_type"],
                    summary=str(entry.get("summary", "")).strip(),
                    reliability=float(feed_meta["reliability"]),
                    collected_at_utc=datetime.now(timezone.utc),
                )
            )
    return articles


def _gdelt_query(symbols: list[str]) -> str:
    terms = ["gold", "Federal Reserve", "inflation", "interest rates", "US dollar", "bond yields"]
    if any(symbol.upper().startswith("EUR") for symbol in symbols):
        terms.extend(["euro", "ECB", "Eurozone inflation"])
    if any(symbol.upper().startswith("GBP") for symbol in symbols):
        terms.extend(["sterling", "Bank of England", "UK inflation"])
    return " OR ".join(f'"{term}"' if " " in term else term for term in terms)


def fetch_gdelt(
    symbols: list[str],
    max_records: int = 75,
    lookback_hours: int = 48,
    timeout: int = 25,
) -> list[RawNewsArticle]:
    query = _gdelt_query(symbols)
    start = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
    params = (
        f"query={quote_plus(query)}&mode=ArtList&maxrecords={min(max_records, 250)}"
        f"&format=json&sort=HybridRel&startdatetime={start.strftime('%Y%m%d%H%M%S')}"
    )
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    articles: list[RawNewsArticle] = []
    for item in data.get("articles", []):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        domain = str(item.get("domain", "") or urlsplit(str(item.get("url", ""))).netloc)
        articles.append(
            RawNewsArticle(
                title=title,
                url=canonicalize_url(str(item.get("url", ""))),
                published_at_utc=_parse_datetime(item.get("seendate")),
                source=domain or "GDELT",
                source_type="global_news_index",
                summary="",
                language=str(item.get("language", "English")),
                reliability=0.65,
                collected_at_utc=datetime.now(timezone.utc),
            )
        )
    return articles


def collect_news(
    symbols: list[str],
    max_per_feed: int = 30,
    gdelt_max_records: int = 75,
    lookback_hours: int = 48,
    include_gdelt: bool = True,
) -> tuple[list[RawNewsArticle], list[str]]:
    errors: list[str] = []
    articles: list[RawNewsArticle] = []
    try:
        articles.extend(fetch_rss(max_per_feed=max_per_feed))
    except Exception as exc:
        errors.append(f"RSS collection failed: {exc}")
    if include_gdelt:
        try:
            articles.extend(fetch_gdelt(symbols, max_records=gdelt_max_records, lookback_hours=lookback_hours))
        except Exception as exc:
            errors.append(f"GDELT collection failed: {exc}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
    deduped: dict[str, RawNewsArticle] = {}
    for article in articles:
        if article.published_at_utc < cutoff:
            continue
        key = article_key(article.title, article.url)
        current = deduped.get(key)
        if current is None or article.reliability > current.reliability:
            deduped[key] = article
    return sorted(deduped.values(), key=lambda item: item.published_at_utc, reverse=True), errors
