from app.models import Decision
from app.engines.risk_engine import evaluate

def test_risk_approves_good_setup():
 d=Decision(symbol='GC=F',bias='bullish',confidence=.7,action='wait_for_pullback',summary='',bullish_case='',bearish_case='')
 r=evaluate(d,10000,2000,1990,2020)
 assert r.approved and r.reward_risk==2
