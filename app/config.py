import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./market_ai.db')
OLLAMA_URL=os.getenv('OLLAMA_URL','http://localhost:11434')
OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','llama3.2:3b')
USE_OLLAMA=os.getenv('USE_OLLAMA','false').lower()=='true'
SYMBOL=os.getenv('SYMBOL','GC=F')
INTERVAL=os.getenv('INTERVAL','1h')
PERIOD=os.getenv('PERIOD','6mo')
RISK_PER_TRADE=float(os.getenv('RISK_PER_TRADE','0.005'))
DAILY_LOSS_LIMIT=float(os.getenv('DAILY_LOSS_LIMIT','0.02'))
