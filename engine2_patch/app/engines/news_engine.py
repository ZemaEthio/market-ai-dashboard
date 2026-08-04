from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable

import requests

from app import config
from app.collectors.news import RawNewsArticle

HIGH_IMPACT_TERMS = {
    "fomc", "rate decision", "interest rate", "inflation", "cpi", "pce", "payroll", "employment",
    "unemployment", "gdp", "powell", "lagarde", "ecb", "federal reserve", "central bank",
    "war", "sanction", "tariff", "ceasefire", "recession", "bond yield", "treasury yield",
}

GOLD_POSITIVE = {
    "rate cut": 0.45, "cuts rates": 0.45, "dovish": 0.35, "lower yields": 0.35,
    "yield falls": 0.30, "weak dollar": 0.35, "dollar falls": 0.30, "recession": 0.30,
    "geopolitical": 0.25, "war": 0.20, "sanctions": 0.20, "safe haven": 0.35,
    "inflation rises": 0.18, "hot inflation": 0.12, "stimulus": 0.20, "liquidity": 0.12,
}
GOLD_NEGATIVE = {
    "rate hike": -0.45, "hikes rates": -0.45, "hawkish": -0.35, "higher yields": -0.35,
    "yield rises": -0.30, "strong dollar": -0.35, "dollar rises": -0.30, "disinflation": -0.15,
    "ceasefire": -0.15, "risk appetite": -0.12,
}
EURUSD_POSITIVE = {
    "ecb rate hike": 0.45, "ecb hawkish": 0.40, "eurozone inflation rises": 0.20,
    "euro strengthens": 0.40, "weak dollar": 0.35, "dollar falls": 0.30,
    "fed rate cut": 0.45, "federal reserve rate cut": 0.45, "fed dovish": 0.40,
    "us recession": 0.25, "us payrolls miss": 0.25,
}
EURUSD_NEGATIVE = {
    "ecb rate cut": -0.45, "ecb dovish": -0.40, "euro weakens": -0.40,
    "strong dollar": -0.35, "dollar rises": -0.30, "fed rate hike": -0.45,
    "federal reserve rate hike": -0.45, "fed hawkish": -0.40,
    "eurozone recession": -0.30, "eurozone inflation falls": -0.15,
}
GENERIC_USD_POSITIVE = {"strong dollar": 0.35, "fed hawkish": 0.35, "rate hike": 0.30, "higher yields": 0.30}
GENERIC_USD_NEGATIVE = {"weak dollar": -0.35, "fed dovish": -0.35, "rate cut": -0.30, "lower yields": -0.30}

SYMBOL_KEYWORDS = {
    "GC=F": {"gold", "bullion", "precious metal", "federal reserve", "fed", "inflation", "yield", "dollar", "geopolitical"},
    "XAUUSD": {"gold", "bullion", "precious metal", "federal reserve", "fed", "inflation", "yield", "dollar", "geopolitical"},
    "EURUSD=X": {"euro", "eurusd", "ecb", "eurozone", "federal reserve", "fed", "dollar", "inflation", "yield"},
    "GBPUSD=X": {"sterling", "pound", "gbpusd", "bank of england", "boe", "federal reserve", "fed", "dollar", "inflation"},
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
        payload = asdict(self)
        return payload


def _normalized_text(article: RawNewsArticle) -> str:
    return re.sub(r"\s+", " ", f"{article.title} {article.summary}".lower()).strip()


def _relevance(text: str, symbol: str) -> float:
    keys = SYMBOL_KEYWORDS.get(symbol.upper()) or {"forex", "currency", "central bank", "inflation", "interest rate", "dollar"}
    matches = sum(1 for key in keys if key in text)
    return min(1.0, matches / 3.0)


def _dictionary_for_symbol(symbol: str) -> dict[str, float]:
    upper = symbol.upper()
    if upper in {"GC=F", "XAUUSD", "XAU/USD"}:
        return {**GOLD_POSITIVE, **GOLD_NEGATIVE}
    if upper in {"EURUSD=X", "EURUSD", "EUR/USD"}:
        return {**EURUSD_POSITIVE, **EURUSD_NEGATIVE}
    if upper.startswith("USD"):
        return {**GENERIC_USD_POSITIVE, **GENERIC_USD_NEGATIVE}
    return {**GENERIC_USD_NEGATIVE, **GENERIC_USD_POSITIVE}


def score_article(article: RawNewsArticle, symbol: str) -> ScoredArticle:
    text = _normalized_text(article)
    relevance = _relevance(text, symbol)
    weights = _dictionary_for_symbol(symbol)
    matched: list[str] = []
    raw_score = 0.0
    for phrase, weight in weights.items():
        if phrase in text:
            matched.append(phrase)
            raw_score += weight

    high_matches = [term for term in HIGH_IMPACT_TERMS if term in text]
    importance_multiplier = 1.35 if high_matches else 1.0
    source_multiplier = 1.20 if article.source_type == "official_central_bank" else 1.0
    score = raw_score * max(0.35, relevance) * importance_multiplier * source_multiplier * article.reliability
    score = max(-1.0, min(1.0, score))

    if abs(score) < 0.06:
        impact = "neutral"
    elif score > 0:
        impact = "bullish"
    else:
        impact = "bearish"
    importance = "high" if high_matches or article.source_type == "official_central_bank" else "medium" if relevance >= 0.67 else "low"
    return ScoredArticle(
        title=article.title,
        url=article.url,
        source=article.source,
        published_at_utc=article.published_at_utc.isoformat(),
        relevance=round(relevance, 4),
        importance=importance,
        impact=impact,
        score=round(score, 4),
        matched_terms=sorted(set(matched + high_matches))[:12],
        reliability=round(article.reliability, 3),
    )


def _deterministic_summary(symbol: str, bias: str, score: float, drivers: list[ScoredArticle], warnings: list[str]) -> str:
    if not drivers:
        return f"No sufficiently relevant recent news was found for {symbol}; the news bias is neutral and confidence is low."
    top = drivers[:3]
    driver_text = "; ".join(f"{item.source}: {item.title}" for item in top)
    warning_text = f" Warning: {'; '.join(warnings)}" if warnings else ""
    return f"{symbol} news bias is {bias} with an aggregate score of {score:+.2f}. Main drivers: {driver_text}.{warning_text}"


def _ollama_summary(symbol: str, bias: str, score: float, drivers: list[ScoredArticle]) -> str:
    prompt = (
        "You are a cautious market-news analyst. Summarize only the supplied headlines. "
        "Do not invent facts, prices, forecasts, or trading instructions. Explain the likely market mechanism in 3 short sentences.\n"
        f"Instrument: {symbol}\nDeterministic bias: {bias}\nDeterministic score: {score:+.3f}\n"
        + "\n".join(f"- [{d.importance}/{d.impact}] {d.title} ({d.source})" for d in drivers[:8])
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
    relevant = [item for item in scored if item.relevance >= 0.34 or item.importance == "high"]
    weighted = [item for item in relevant if abs(item.score) >= 0.01]

    total_weight = sum(max(0.25, item.relevance) * item.reliability for item in weighted)
    aggregate = (
        sum(item.score * max(0.25, item.relevance) * item.reliability for item in weighted) / total_weight
        if total_weight else 0.0
    )
    aggregate = max(-1.0, min(1.0, aggregate))
    if aggregate >= 0.08:
        bias = "bullish"
    elif aggregate <= -0.08:
        bias = "bearish"
    else:
        bias = "mixed" if weighted else "neutral"

    non_neutral = [item for item in weighted if item.impact != "neutral"]
    agreement = 0.0
    if non_neutral:
        dominant = max(sum(item.score > 0 for item in non_neutral), sum(item.score < 0 for item in non_neutral))
        agreement = dominant / len(non_neutral)
    source_count = len({item.source for item in relevant})
    coverage = min(1.0, len(relevant) / 12.0)
    diversity = min(1.0, source_count / 5.0)
    confidence = 0.20 + 0.30 * coverage + 0.20 * diversity + 0.20 * agreement + 0.10 * min(1.0, abs(aggregate) * 2)
    confidence = round(min(0.90, max(0.10, confidence)), 4)

    high_impact_count = sum(item.importance == "high" for item in relevant)
    drivers = sorted(relevant, key=lambda item: (item.importance == "high", abs(item.score), item.relevance), reverse=True)[:10]
    warnings: list[str] = []
    if len(relevant) < 3:
        warnings.append("Low relevant-article coverage")
    if source_count < 2:
        warnings.append("Limited source diversity")
    if non_neutral and agreement < 0.60:
        warnings.append("News signals conflict")
    if not items:
        warnings.append("No articles were collected")

    deterministic = _deterministic_summary(symbol, bias, aggregate, drivers, warnings)
    model_name = "deterministic-v1"
    summary = deterministic
    should_use_ollama = config.USE_OLLAMA if use_ollama is None else use_ollama
    if should_use_ollama and drivers:
        try:
            summary = _ollama_summary(symbol, bias, aggregate, drivers)
            model_name = config.OLLAMA_MODEL
        except Exception as exc:
            warnings.append(f"Ollama unavailable; deterministic summary used ({type(exc).__name__})")

    quality = "ok" if items and len(relevant) >= 3 else "limited"
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
