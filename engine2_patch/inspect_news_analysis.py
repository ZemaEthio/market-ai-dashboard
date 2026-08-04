from __future__ import annotations

import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--database", default="data/market_ai.db")
parser.add_argument("--limit", type=int, default=20)
args = parser.parse_args()

with sqlite3.connect(args.database) as connection:
    rows = connection.execute(
        """
        SELECT id, symbol, analyzed_at_utc, article_count, relevant_article_count,
               source_count, bias, ROUND(score, 4), ROUND(confidence, 4),
               high_impact_count, model_name, data_quality, summary
        FROM news_analyses
        ORDER BY id DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()
    article_stats = connection.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT source), MIN(published_at_utc), MAX(published_at_utc)
        FROM news_articles
        """
    ).fetchone()

print("NEWS ARTICLE STORE")
print(article_stats)
print("\nLATEST ENGINE 2 ANALYSES")
for row in rows:
    print(row)
if not rows:
    print("No news analyses yet.")
