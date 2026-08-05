from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))
st.set_page_config(page_title="Learn & Trade | ZEMA Market AI", page_icon="🎓", layout="wide")
st.title("🎓 Learn → Practice → Paper Trade")
st.caption("Education-gated simulated trading with decision evidence and market-moving news. No live execution.")

def now(): return datetime.now(timezone.utc).isoformat()
def con():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c

def table(name):
    with con() as c: return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None
if not all(table(x) for x in ("paper_accounts","paper_trades","education_progress")):
    st.error("Run `python init_paper_trading.py` first."); st.stop()

def q(sql, params=()):
    with con() as c: return pd.read_sql_query(sql,c,params=params)
def execute(sql, params=()):
    with con() as c: c.execute(sql,params); c.commit()

def account_rows(): return q("SELECT * FROM paper_accounts ORDER BY id")
def trade_rows(a):
    d=q("SELECT * FROM paper_trades WHERE account_id=? ORDER BY planned_at_utc DESC,id DESC",(a,))
    return d

def latest_decision(symbol):
    if not table("decision_analyses"): return None
    with con() as c:
        d=c.execute("SELECT * FROM decision_analyses WHERE symbol=? ORDER BY decided_at_utc DESC,id DESC LIMIT 1",(symbol,)).fetchone()
        if not d: return None
        r=c.execute("SELECT * FROM risk_evaluations WHERE decision_analysis_id=? ORDER BY evaluated_at_utc DESC,id DESC LIMIT 1",(d['id'],)).fetchone() if table('risk_evaluations') else None
        return dict(d), (dict(r) if r else None)

def news_category(text):
    t=(text or '').lower()
    groups={
      'Central banks':['federal reserve','fomc','ecb','bank of england','interest rate','powell','lagarde'],
      'Inflation & jobs':['inflation','cpi','pce','payroll','employment','unemployment','wage'],
      'Growth & demand':['gdp','retail sales','pmi','consumer confidence','recession'],
      'Rates & credit':['treasury','bond yield','debt ceiling','credit downgrade','banking crisis'],
      'Geopolitics & trade':['war','sanction','tariff','ceasefire','election','trade conflict'],
      'Energy & commodities':['oil','opec','natural gas','gold','commodity'],
      'Global risk':['china','japan','yen','volatility','risk sentiment','equity selloff'],
    }
    for k,words in groups.items():
        if any(w in t for w in words): return k
    return 'Other market news'

LESSONS={
 'risk':('Risk before reward','Risk a fixed fraction of equity. Define invalidation first; position size comes from stop distance, not desired profit.',
         [('What should determine position size?', ['Desired profit','Stop distance and account risk','Trade confidence only'],1),
          ('A valid BUY structure is:', ['stop < entry < target','target < entry < stop','entry < stop < target'],0),
          ('Minimum reward-to-risk used here?', ['0.5R','1.0R','1.5R'],2)]),
 'news':('Trading around news','High-impact data and central-bank communication can change volatility, spreads, and direction. A good setup can still be a bad trade near a major release.',
         [('Which is usually high impact?', ['CPI or rate decision','A minor blog post','Old price data'],0),
          ('Near major news you should:', ['Ignore timing','Reduce risk or wait','Increase leverage'],1),
          ('News evidence should be:', ['Timestamped and sourced','Based on rumors','Used without context'],0)]),
 'regime':('Market regime and invalidation','Trending and ranging markets reward different entries. Invalidation is the price or condition proving the thesis wrong.',
         [('In a range, chasing breakout candles is:', ['Always required','Often risky without confirmation','Risk-free'],1),
          ('Invalidation should be:', ['Specific and testable','Changed after entry to avoid loss','Undefined'],0),
          ('A regime label helps:', ['Choose tactics appropriate to conditions','Guarantee profit','Remove stop losses'],0)]),
}

acc=account_rows()
if acc.empty:
    with st.form('create'):
        n=st.text_input('Account name','Forex Practice'); b=st.number_input('Starting balance',100.0,1000000.0,10000.0,500.0)
        if st.form_submit_button('Create account'):
            execute("INSERT INTO paper_accounts(name,starting_balance,current_balance,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?)",(n.strip(),b,b,now(),now())); st.rerun()
    st.stop()
with st.sidebar:
    opts={int(r.id):f"{r['name']} · ${r['current_balance']:,.2f}" for _,r in acc.iterrows()}
    aid=st.selectbox('Paper account',list(opts),format_func=lambda x:opts[x])
    mode=st.radio('Mode',['Learning','Practice','Paper Trading'],index=2)
account=acc[acc.id==aid].iloc[0]; balance=float(account.current_balance)
progress=q("SELECT * FROM education_progress WHERE account_id=?",(aid,))
passed=set(progress.loc[progress.passed==1,'lesson_key']) if not progress.empty else set()
readiness=(len(passed)/len(LESSONS))*70
trades=trade_rows(aid); closed=trades[trades.status=='CLOSED'] if not trades.empty else pd.DataFrame()
if not closed.empty:
    discipline=(pd.to_numeric(closed.quiz_score,errors='coerce').fillna(0)>=80).mean()*20
    journal=(closed.lessons.fillna('').str.len()>10).mean()*10
    readiness=min(100,readiness+discipline+journal)
cols=st.columns(5); cols[0].metric('Balance',f"${balance:,.2f}"); cols[1].metric('Readiness',f"{readiness:.0f}%"); cols[2].metric('Lessons passed',f"{len(passed)}/{len(LESSONS)}"); cols[3].metric('Open',int((trades.status=='OPEN').sum()) if not trades.empty else 0); cols[4].metric('Closed',len(closed))

learn, news, plan, manage, journal, performance = st.tabs(['Learn','Market-moving news','Plan Trade','Manage','Journal','Performance'])
with learn:
    st.subheader('Trading academy')
    for key,(title,body,questions) in LESSONS.items():
        with st.expander(('✅ ' if key in passed else '📘 ')+title, expanded=key not in passed):
            st.write(body)
            with st.form('quiz_'+key):
                answers=[]
                for i,(question,choices,correct) in enumerate(questions): answers.append(st.radio(question,choices,key=f'{key}_{i}'))
                if st.form_submit_button('Submit lesson'):
                    score=sum(answers[i]==questions[i][1][questions[i][2]] for i in range(len(questions)))/len(questions)*100
                    execute("INSERT INTO education_progress(account_id,lesson_key,lesson_title,score,passed,answers_json,completed_at_utc) VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id,lesson_key) DO UPDATE SET score=excluded.score,passed=excluded.passed,answers_json=excluded.answers_json,completed_at_utc=excluded.completed_at_utc",(aid,key,title,score,int(score>=80),json.dumps(answers),now()))
                    st.success(f'Score: {score:.0f}% — '+('passed' if score>=80 else 'review and retry')); st.rerun()
with news:
    st.subheader('News that can move FX, gold, rates, and risk sentiment')
    st.caption('Coverage includes central banks, inflation/jobs, growth, rates/credit, geopolitics/trade, energy/commodities, and global risk.')
    if not table('news_articles'): st.info('No news table found. Run the normal data collection workflow.')
    else:
        n=q("SELECT title,source,source_type,published_at_utc,reliability,url FROM news_articles ORDER BY published_at_utc DESC LIMIT 150")
        if n.empty: st.info('No collected articles yet. Run `python collect_data.py` or the GitHub refresh workflow.')
        else:
            n['category']=n.title.map(news_category); cats=['All']+sorted(n.category.unique().tolist()); cat=st.selectbox('Category',cats)
            view=n if cat=='All' else n[n.category==cat]
            for _,r in view.head(50).iterrows():
                impact='HIGH' if r.category in {'Central banks','Inflation & jobs','Geopolitics & trade','Rates & credit'} else 'MEDIUM'
                st.markdown(f"**{impact} · {r['category']}** — {r['title']}")
                st.caption(f"{r['source']} · {r['published_at_utc']} · reliability {float(r['reliability']):.0%}")
with plan:
    st.subheader('Evidence-linked trade plan')
    symbol=st.selectbox('Symbol',['EURUSD=X','GC=F']); decision=latest_decision(symbol)
    engine_action='WAIT'; engine_conf=0.0; decision_id=None; risk_id=None; evidence={}
    if decision:
        d,r=decision; engine_action=d.get('preferred_action','WAIT'); engine_conf=float(d.get('confidence') or 0); decision_id=d.get('id'); risk_id=r.get('id') if r else None
        evidence={'decision':d,'risk':r}; st.info(f"Engine: {engine_action} · confidence {engine_conf:.1%} · alignment {d.get('alignment')} · risk {d.get('risk_level')}")
    gated=not {'risk','news','regime'}.issubset(passed)
    if gated: st.warning('Pass all three lessons before saving a paper trade. Planning remains available for practice.')
    with st.form('plan'):
        c1,c2,c3,c4=st.columns(4); direction=c1.selectbox('Direction',['BUY','SELL']); timeframe=c2.selectbox('Timeframe',['15m','1h','4h','1d']); risk_pct=c3.number_input('Risk %',0.1,2.0,0.5,0.1); regime=c4.selectbox('Regime',['Trending','Ranging','High volatility','Low volatility','Unclear'])
        base=1.1 if symbol=='EURUSD=X' else 2400.0; a,b,c=st.columns(3); entry=a.number_input('Entry',0.00001,value=base,format='%.5f'); stop=b.number_input('Stop',0.00001,value=base*(.995 if direction=='BUY' else 1.005),format='%.5f'); target=c.number_input('Target',0.00001,value=base*(1.01 if direction=='BUY' else .99),format='%.5f')
        thesis=st.text_area('Your market view and thesis'); invalid=st.text_area('Exact invalidation condition'); setup=st.text_input('Setup name','Evidence-linked setup')
        checks=[st.checkbox('I reviewed trend/regime'),st.checkbox('I checked economic and geopolitical news'),st.checkbox('I accept the stop and position size'),st.checkbox('No revenge/FOMO trading')]
        submit=st.form_submit_button('Save paper-trade plan',disabled=(mode!='Paper Trading'))
    sd=(entry-stop if direction=='BUY' else stop-entry); rd=(target-entry if direction=='BUY' else entry-target); valid=sd>0 and rd>0; rr=rd/sd if valid else 0; risk=balance*risk_pct/100; units=risk/sd if valid else 0
    st.write(f"Risk **${risk:,.2f}** · Units **{units:,.2f}** · Reward/risk **{rr:.2f}R**")
    if submit:
        errors=[]
        if gated: errors.append('Complete all lessons')
        if not valid: errors.append('Invalid entry/stop/target structure')
        if rr<1.5: errors.append('Reward/risk must be at least 1.5R')
        if not all(checks): errors.append('Complete the checklist')
        if not thesis.strip() or not invalid.strip(): errors.append('Add thesis and invalidation')
        if engine_action in {'WAIT','NO_TRADE'}: errors.append('Current engine decision is WAIT/NO TRADE')
        if errors: st.error(' · '.join(errors))
        else:
            lesson='risk,news,regime'; quiz=float(progress.score.mean()) if not progress.empty else 0
            execute("""INSERT INTO paper_trades(account_id,symbol,direction,status,timeframe,setup_name,market_regime,entry_price,stop_price,target_price,risk_percent,risk_amount,units,reward_risk_ratio,planned_at_utc,confidence,thesis,invalidation,pre_trade_checklist,decision_analysis_id,risk_evaluation_id,evidence_snapshot_json,education_lesson,quiz_score,readiness_score,user_market_view,engine_market_view,created_at_utc,updated_at_utc) VALUES(?,?,?,'PLANNED',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid,symbol,direction,timeframe,setup,regime,entry,stop,target,risk_pct,risk,units,rr,now(),engine_conf,thesis,invalid,json.dumps(checks),decision_id,risk_id,json.dumps(evidence,default=str),lesson,quiz,readiness,thesis,engine_action,now(),now()))
            st.success('Evidence-linked paper trade saved.'); st.rerun()
with manage:
    active=trades[trades.status.isin(['PLANNED','OPEN'])] if not trades.empty else pd.DataFrame()
    if active.empty: st.info('No planned or open trades.')
    for _,t in active.iterrows():
        with st.expander(f"#{int(t.id)} {t.symbol} {t.direction} · {t.status}"):
            st.write(t.thesis)
            if t.status=='PLANNED':
                if st.button('Open simulated trade',key=f'o{t.id}'): execute("UPDATE paper_trades SET status='OPEN',opened_at_utc=?,updated_at_utc=? WHERE id=?",(now(),now(),int(t.id))); st.rerun()
            else:
                with st.form(f'c{t.id}'):
                    ep=st.number_input('Exit price',0.00001,value=float(t.entry_price),format='%.5f'); costs=st.number_input('Costs',0.0,value=0.0); lesson=st.text_area('Post-trade lesson')
                    if st.form_submit_button('Close trade'):
                        mult=1 if t.direction=='BUY' else -1; gross=(ep-t.entry_price)*t.units*mult; net=gross-costs; rm=net/t.risk_amount if t.risk_amount else 0
                        execute("UPDATE paper_trades SET status='CLOSED',closed_at_utc=?,exit_price=?,gross_pnl=?,costs=?,net_pnl=?,r_multiple=?,lessons=?,updated_at_utc=? WHERE id=?",(now(),ep,gross,costs,net,rm,lesson,now(),int(t.id)))
                        execute("UPDATE paper_accounts SET current_balance=current_balance+?,updated_at_utc=? WHERE id=?",(net,now(),aid)); st.rerun()
with journal:
    if trades.empty: st.info('No trades yet.')
    else: st.dataframe(trades,use_container_width=True,hide_index=True); st.download_button('Download journal CSV',trades.to_csv(index=False).encode(),f'zema_journal_{aid}.csv','text/csv')
with performance:
    if closed.empty: st.info('Close trades to see performance.')
    else:
        x=closed.copy(); x['net_pnl']=pd.to_numeric(x.net_pnl,errors='coerce').fillna(0); x=x.iloc[::-1]; x['equity']=float(account.starting_balance)+x.net_pnl.cumsum()
        a,b,c,d=st.columns(4); a.metric('Net P&L',f"${x.net_pnl.sum():,.2f}"); b.metric('Win rate',f"{(x.net_pnl>0).mean():.1%}"); c.metric('Average R',f"{pd.to_numeric(x.r_multiple,errors='coerce').mean():.2f}"); d.metric('Avg readiness',f"{pd.to_numeric(x.readiness_score,errors='coerce').mean():.0f}%")
        st.plotly_chart(go.Figure(go.Scatter(x=x.closed_at_utc,y=x.equity,mode='lines+markers')),use_container_width=True)
        for group in ['symbol','market_regime','engine_market_view']:
            if group in x: st.write(group.replace('_',' ').title()); st.dataframe(x.groupby(group).net_pnl.agg(['count','sum','mean']).reset_index(),hide_index=True,use_container_width=True)
