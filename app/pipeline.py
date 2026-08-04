from app import config
from app.collectors.market import fetch_prices
from app.collectors.news import fetch_rss,fetch_gdelt
from app.engines.market_engine import analyze_market
from app.engines.news_engine import analyze_news
from app.engines.decision_engine import decide

def run(symbol=None):
    symbol=symbol or config.SYMBOL
    market=analyze_market(fetch_prices(symbol,config.PERIOD,config.INTERVAL),symbol)
    news=analyze_news(fetch_rss()+fetch_gdelt())
    decision=decide(market,news)
    return {'market':market.model_dump(),'news':news.model_dump(),'decision':decision.model_dump()}
