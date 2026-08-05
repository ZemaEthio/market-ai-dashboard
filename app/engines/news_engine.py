from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

import requests

from app import config
from app.collectors.news import RawNewsArticle, event_key

EVENT_CATEGORIES = {
    "central_bank": {"fomc", "federal reserve", "fed", "ecb", "bank of england", "boe", "rate decision", "monetary policy", "powell", "lagarde"},
    "inflation": {"inflation", "cpi", "pce", "producer prices", "ppi", "core prices"},
    "employment": {"payroll", "employment", "unemployment", "jobless claims", "wages", "labor market"},
    "growth": {"gdp", "recession", "retail sales", "industrial production", "pmi", "consumer confidence"},
    "rates_credit": {"treasury yield", "bond yield", "real yield", "credit spread", "default", "banking stress", "liquidity"},
    "geopolitics": {"war", "sanction", "ceasefire", "missile", "invasion", "geopolitical", "conflict", "tariff", "trade war"},
    "energy_commodities": {"oil", "gas", "opec", "commodity", "gold mine", "mining disruption", "supply disruption"},
    "currency": {"dollar", "euro", "sterling", "yen", "currency", "fx", "exchange rate"},
}

HIGH_IMPACT_CATEGORIES = {"central_bank", "inflation", "employment", "geopolitics"}

INSTRUMENT_PROFILES = {
    "GC=F": {
        "aliases": {"gold", "bullion", "precious metal", "xau"},
        "macro": {"fed", "federal reserve", "inflation", "real yield", "treasury yield", "dollar", "geopolitical", "central bank gold", "recession", "banking stress", "sanction", "tariff", "oil"},
        "positive": {
            "rate cut": 0.50, "dovish": 0.38, "lower yields": 0.40, "yield falls": 0.34,
            "real yields fall": 0.45, "weak dollar": 0.40, "dollar falls": 0.34,
            "recession": 0.30, "banking stress": 0.34, "war": 0.25, "geopolitical": 0.25,
            "sanctions": 0.18, "central bank gold buying": 0.42, "safe haven": 0.38,
            "mine disruption": 0.22, "supply disruption": 0.18,
        },
        "negative": {
            "rate hike": -0.50, "hawkish": -0.38, "higher yields": -0.40, "yield rises": -0.34,
            "real yields rise": -0.45, "strong dollar": -0.40, "dollar rises": -0.34,
            "ceasefire": -0.16, "risk appetite": -0.16, "central bank gold selling": -0.42,
        },
    },
    "XAUUSD": {},
    "EURUSD=X": {
        "aliases": {"euro", "eurusd", "euro zone", "eurozone"},
        "macro": {"ecb", "fed", "federal reserve", "eurozone inflation", "us inflation", "payroll", "gdp", "yield", "dollar", "energy", "european politics", "tariff"},
        "positive": {
            "ecb rate hike": 0.50, "ecb hawkish": 0.44, "eurozone inflation rises": 0.24,
            "eurozone growth beats": 0.28, "euro strengthens": 0.42, "weak dollar": 0.38,
            "dollar falls": 0.34, "fed rate cut": 0.50, "fed dovish": 0.44,
            "us payrolls miss": 0.30, "us recession": 0.28, "european energy prices fall": 0.20,
        },
        "negative": {
            "ecb rate cut": -0.50, "ecb dovish": -0.44, "euro weakens": -0.42,
            "strong dollar": -0.38, "dollar rises": -0.34, "fed rate hike": -0.50,
            "fed hawkish": -0.44, "eurozone recession": -0.34, "eurozone inflation falls": -0.18,
            "european energy crisis": -0.30, "european political risk": -0.20,
        },
    },
    "GBPUSD=X": {
        "aliases": {"sterling", "pound", "gbpusd", "british pound"},
        "macro": {"bank of england", "boe", "fed", "uk inflation", "us inflation", "payroll", "gdp", "yield", "dollar", "uk politics", "tariff"},
        "positive": {"boe rate hike": 0.50, "boe hawkish": 0.44, "sterling strengthens": 0.42, "weak dollar": 0.38, "fed rate cut": 0.50, "uk growth beats": 0.26},
        "negative": {"boe rate cut": -0.50, "boe dovish": -0.44, "sterling weakens": -0.42, "strong dollar": -0.38, "fed rate hike": -0.50, "uk recession": -0.32},
    },
}
INSTRUMENT_PROFILES["XAUUSD"] = INSTRUMENT_PROFILES["GC=F"]

SOURCE_MULTIPLIERS = {
    "official_central_bank": 1.25,
    "official_statistics": 1.25,
    "official_government": 1.18,
    "official_multilateral": 1.15,
    "global_news_index": 0.95,
}


@dataclass(slots=True)
class ScoredArticle:
    title: str
    url: str
    source: str
    published_at_utc: str
    relevance: float
    importance: str
    impact: str
    score: float
    matched_terms: list[str]
    reliability: float
    category: str = "other"
    freshness: float = 1.0
    event_key: str = ""


@dataclass(slots=True)
class NewsAnalysis:
    symbol: str
    analyzed_at_utc: str
    article_count: int
    relevant_article_count: int
    source_count: int
    bias: str
    score: float
    confidence: float
    high_impact_count: int
    summary: str
    drivers: list[ScoredArticle]
    warnings: list[str]
    model_name: str
    data_quality: str

    def to_dict(self) -> dict:
        return asdict(self)


def _text(article: RawNewsArticle) -> str:
    return re.sub(r"\s+", " ", f"{article.title} {article.summary}".lower()).strip()


def _profile(symbol: str) -> dict:
    upper = symbol.upper().replace("/", "")
    if upper in INSTRUMENT_PROFILES:
        return INSTRUMENT_PROFILES[upper]
    return {
        "aliases": {symbol.lower()},
        "macro": {"central bank", "inflation", "interest rate", "dollar", "yield", "growth", "geopolitical"},
        "positive": {"weak dollar": 0.30, "rate cut": 0.25},
        "negative": {"strong dollar": -0.30, "rate hike": -0.25},
    }


def _category(text: str) -> tuple[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for category, terms in EVENT_CATEGORIES.items():
        matches = sorted(term for term in terms if term in text)
        if matches:
            hits[category] = matches
    if not hits:
        return "other", []
    category = max(hits, key=lambda key: (len(hits[key]), key in HIGH_IMPACT_CATEGORIES))
    return category, hits[category]


def _freshness(article: RawNewsArticle, category: str) -> float:
    published = article.published_at_utc
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).total_seconds() / 3600.0)
    half_life = 36.0 if category in {"central_bank", "inflation", "employment"} else 24.0
    return max(0.08, math.exp(-math.log(2) * age_hours / half_life))


def _relevance(text: str, symbol: str) -> tuple[float, list[str]]:
    profile = _profile(symbol)
    alias_matches = sorted(term for term in profile["aliases"] if term in text)
    macro_matches = sorted(term for term in profile["macro"] if term in text)
    # Explicit instrument mention is strongest; macro-only articles still qualify if several mechanisms match.
    score = min(1.0, 0.58 * min(1.0, len(alias_matches)) + 0.18 * min(3, len(macro_matches)))
    return score, alias_matches + macro_matches


def score_article(article: RawNewsArticle, symbol: str) -> ScoredArticle:
    text = _text(article)
    profile = _profile(symbol)
    relevance, relevance_terms = _relevance(text, symbol)
    category, category_terms = _category(text)

    matched: list[str] = []
    raw_score = 0.0
    for phrase, weight in {**profile["positive"], **profile["negative"]}.items():
        if phrase in text:
            matched.append(phrase)
            raw_score += weight

    importance_multiplier = 1.35 if category in HIGH_IMPACT_CATEGORIES else 1.15 if category != "other" else 1.0
    source_multiplier = SOURCE_MULTIPLIERS.get(article.source_type, 1.0)
    freshness = _freshness(article, category)
    score = raw_score * relevance * importance_multiplier * source_multiplier * article.reliability * freshness
    score = max(-1.0, min(1.0, score))

    if abs(score) < 0.04:
        impact = "neutral"
    elif score > 0:
        impact = "bullish"
    else:
        impact = "bearish"

    if category in HIGH_IMPACT_CATEGORIES and relevance >= 0.40:
        importance = "high"
    elif category != "other" and relevance >= 0.30:
        importance = "medium"
    else:
        importance = "low"

    return ScoredArticle(
        title=article.title,
        url=article.url,
        source=article.source,
        published_at_utc=article.published_at_utc.isoformat(),
        relevance=round(relevance, 4),
        importance=importance,
        impact=impact,
        score=round(score, 4),
        matched_terms=sorted(set(relevance_terms + category_terms + matched))[:16],
        reliability=round(article.reliability, 3),
        category=category,
        freshness=round(freshness, 4),
        event_key=event_key(article.title),
    )


def _dedupe_events(items: list[ScoredArticle]) -> list[ScoredArticle]:
    """Keep at most two strong articles for one event cluster."""
    grouped: dict[str, list[ScoredArticle]] = {}
    for item in items:
        grouped.setdefault(item.event_key or item.title.lower(), []).append(item)
    selected: list[ScoredArticle] = []
    for group in grouped.values():
        group.sort(key=lambda x: (x.reliability, x.relevance, abs(x.score), x.freshness), reverse=True)
        selected.extend(group[:2])
    return selected


def _deterministic_summary(symbol: str, bias: str, score: float, drivers: list[ScoredArticle], warnings: list[str]) -> str:
    if not drivers:
        return f"No sufficiently relevant recent news was found for {symbol}; news bias is neutral and confidence is low."
    positives = [d for d in drivers if d.score > 0][:2]
    negatives = [d for d in drivers if d.score < 0][:2]
    parts = [f"{symbol} news bias is {bias} with an aggregate score of {score:+.2f}."]
    if positives:
        parts.append("Bullish drivers: " + "; ".join(f"{d.category}: {d.title}" for d in positives) + ".")
    if negatives:
        parts.append("Bearish drivers: " + "; ".join(f"{d.category}: {d.title}" for d in negatives) + ".")
    if warnings:
        parts.append("Caution: " + "; ".join(warnings[:2]) + ".")
    return " ".join(parts)


def _ollama_summary(symbol: str, bias: str, score: float, drivers: list[ScoredArticle]) -> str:
    prompt = (
        "You are a cautious market-news analyst. Summarize only the supplied headlines. "
        "Do not invent facts, prices, forecasts, or trading instructions. Explain transmission mechanisms and conflicting evidence in 4 short sentences.\n"
        f"Instrument: {symbol}\nDeterministic bias: {bias}\nDeterministic score: {score:+.3f}\n"
        + "\n".join(f"- [{d.category}/{d.importance}/{d.impact}] {d.title} ({d.source})" for d in drivers[:10])
    )
    response = requests.post(
        config.OLLAMA_URL.rstrip("/") + "/api/generate",
        json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=90,
    )
    response.raise_for_status()
    text = str(response.json().get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama returned an empty response")
    return text


def analyze_news(articles: Iterable[RawNewsArticle], symbol: str, use_ollama: bool | None = None) -> NewsAnalysis:
    items = list(articles)
    scored = [score_article(article, symbol) for article in items]
    relevant = [item for item in scored if item.relevance >= 0.30]
    relevant = _dedupe_events(relevant)
    directional = [item for item in relevant if abs(item.score) >= 0.015]

    # Weight the actual directional score once. score already includes relevance, reliability and freshness.
    weights = [max(0.10, item.relevance * item.reliability * item.freshness) for item in directional]
    total_weight = sum(weights)
    aggregate = sum(item.score * weight for item, weight in zip(directional, weights)) / total_weight if total_weight else 0.0
    aggregate = max(-1.0, min(1.0, aggregate))

    if aggregate >= 0.07:
        bias = "bullish"
    elif aggregate <= -0.07:
        bias = "bearish"
    else:
        bias = "mixed" if directional else "neutral"

    non_neutral = [item for item in directional if item.impact != "neutral"]
    agreement = 0.0
    if non_neutral:
        positive = sum(item.score > 0 for item in non_neutral)
        negative = sum(item.score < 0 for item in non_neutral)
        agreement = max(positive, negative) / len(non_neutral)

    source_count = len({item.source for item in relevant})
    category_count = len({item.category for item in relevant if item.category != "other"})
    official_count = sum(item.reliability >= 0.95 for item in relevant)
    coverage = min(1.0, len(relevant) / 10.0)
    diversity = min(1.0, source_count / 5.0)
    category_diversity = min(1.0, category_count / 4.0)
    official_share = min(1.0, official_count / max(1, len(relevant)))
    confidence = (
        0.12 + 0.24 * coverage + 0.16 * diversity + 0.12 * category_diversity
        + 0.15 * official_share + 0.13 * agreement + 0.08 * min(1.0, abs(aggregate) * 3)
    )
    confidence = round(min(0.92, max(0.08, confidence)), 4)

    high_impact_count = sum(item.importance == "high" for item in relevant)
    drivers = sorted(
        relevant,
        key=lambda item: (item.importance == "high", abs(item.score), item.relevance, item.reliability, item.freshness),
        reverse=True,
    )[:12]

    warnings: list[str] = []
    if len(relevant) < 3:
        warnings.append("Low relevant-article coverage")
    if source_count < 2:
        warnings.append("Limited source diversity")
    if category_count < 2 and len(relevant) >= 3:
        warnings.append("News is concentrated in one event category")
    if non_neutral and agreement < 0.60:
        warnings.append("Bullish and bearish news signals conflict")
    if not items:
        warnings.append("No articles were collected")
    if relevant and sum(item.freshness for item in relevant) / len(relevant) < 0.35:
        warnings.append("Most relevant news is aging")

    summary = _deterministic_summary(symbol, bias, aggregate, drivers, warnings)
    model_name = "deterministic-v2-instrument-aware"
    should_use_ollama = config.USE_OLLAMA if use_ollama is None else use_ollama
    if should_use_ollama and drivers:
        try:
            summary = _ollama_summary(symbol, bias, aggregate, drivers)
            model_name = config.OLLAMA_MODEL
        except Exception as exc:
            warnings.append(f"Ollama unavailable; deterministic summary used ({type(exc).__name__})")

    quality = "ok" if len(relevant) >= 3 and source_count >= 2 else "limited"
    return NewsAnalysis(
        symbol=symbol,
        analyzed_at_utc=datetime.now(timezone.utc).isoformat(),
        article_count=len(items),
        relevant_article_count=len(relevant),
        source_count=source_count,
        bias=bias,
        score=round(aggregate, 4),
        confidence=confidence,
        high_impact_count=high_impact_count,
        summary=summary,
        drivers=drivers,
        warnings=warnings,
        model_name=model_name,
        data_quality=quality,
    )
