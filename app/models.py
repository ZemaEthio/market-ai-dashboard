from pydantic import BaseModel, Field
from typing import Literal

Bias=Literal['bullish','bearish','neutral','mixed']
class MarketSignal(BaseModel):
    symbol:str; bias:Bias; confidence:float=Field(ge=0,le=1)
    regime:str; last_price:float; atr:float; rsi:float
    support:list[float]; resistance:list[float]; reasons:list[str]
class NewsItem(BaseModel):
    title:str; link:str=''; published:str=''; score:float=0; impact:str='neutral'
class NewsSignal(BaseModel):
    bias:Bias; confidence:float=Field(ge=0,le=1); items:list[NewsItem]; summary:str
class Decision(BaseModel):
    symbol:str; bias:Bias; confidence:float=Field(ge=0,le=1)
    action:str; summary:str; bullish_case:str; bearish_case:str
    invalidation:float|None=None; warnings:list[str]=[]
class RiskResult(BaseModel):
    approved:bool; position_units:float; max_loss:float; reward_risk:float
    reasons:list[str]
