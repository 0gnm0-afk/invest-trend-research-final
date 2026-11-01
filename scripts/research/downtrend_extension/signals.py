"""Fixed bearish events. Indicators observe only the completed current bar.

Borrow the audited numeric indicator implementations from the preceding upside
extension; select no thresholds using bearish outcomes. Original benchmark
flags and observable context are calculated by the archived original source.
"""
from pathlib import Path
import importlib.util
import numpy as np
from legacy import roll,lag,ema,wilder,ratio,cross

ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value
shared=module('extension_formula_source',ROOT/'scripts/research/uptrend_extension/signals.py')
original=module('original_downtrend_features',ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research/features.py')
supertrend=shared.supertrend;psar=shared.psar
META={}
BENCHMARKS=['macd_rsi60','macd_positive','cci100_up20','rsi60','stoch80','price5']

def fractal_level(low):
    """Strict five-bar low pivot becomes known after its two right-hand bars."""
    n=len(low);line=np.full(n,np.nan);last=np.nan
    for t in range(n):
        if t>=4 and low[t-2]<min(low[t-4],low[t-3],low[t-1],low[t]):last=low[t-2]
        line[t]=last
    return line

def calculate(z):
    c,o,h,l,v=[np.asarray(z[k],float) for k in ['close','open','high','low','volume']]
    _,_,_,_,cv,aux=shared.calculate(z)
    prior,priorids,ctx,atr=original.calculate(z)
    n=len(c);d={}
    def add(key,label,family,formula,value):
        a=np.asarray(value,float).copy();a[:min(65,n)]=np.nan
        d[key]=a;META[key]=dict(id=key,label=label,family=family,kind='event',formula=formula)
    add('supertrend','슈퍼트렌드 하락 전환','Supertrend','Wilder ATR10 ×3; recursive bands; bullish-to-bearish close-confirmed flip',cross(aux['st_direction'],0))
    add('psar','파라볼릭 SAR 하락 반전','SAR','PSAR .02/.02/.20; bullish-to-bearish reversal, known at current close',cross(aux['ps_direction'],0))
    add('trix_zero','TRIX18 0선 이탈','TRIX','100*(triple EMA18[t]/triple EMA18[t-1]-1) crosses below0',cross(aux['trix'],0))
    add('trix_signal','TRIX18 신호선 이탈','TRIX','TRIX18 crosses below EMA9(TRIX18)',cross(aux['trix'],aux['trix_signal']))
    add('stochrsi80','StochRSI K80 이탈','StochRSI','Wilder RSI14, range14, SMA3 K; K crosses below80; zero range unknown',cross(aux['sk'],80))
    add('stochrsi_cross','StochRSI 고위 K/D 교차','StochRSI','K crosses below SMA3(K), previous K>=80',cross(aux['sk'],aux['sd'])*(lag(aux['sk'])>=80))
    for q in [70,50]:add('rmi'+str(q),'RMI'+str(q)+' 이탈','RMI',f'Wilder20 of positive/negative 5-day close differences; crosses below{q}',cross(aux['rmi'],q))
    add('chaikin','체이킨 0선 이탈','Chaikin','EMA3(ADL)-EMA10(ADL) crosses below0; H=L contributes0 to ADL',cross(aux['chaikin'],0))
    vf=cross(c,aux['avwap']);vf[aux['avwap_age']<5]=np.nan
    add('avwap_quarter','분기 고정 VWAP 대용치 이탈','AVWAP proxy','C crosses below cumulative TP*V/sum(V), calendar quarter/segment anchor, at least5 previous anchor bars',vf)
    add('volume_osc','거래량 오실레이터·하락일','Volume oscillator','SMA5(V)/SMA20(V)-1 crosses above0 AND C<previous C',cross(np.zeros(n),aux['volume_osc'])*(c<lag(c)))
    line=fractal_level(l);aux['fractal_low']=line
    add('fractal_break','확정 프랙탈 저점 이탈','Fractal','Strict5-bar low pivot confirmed at pivot+2; close crosses below latest confirmed pivot low; never backdated',cross(c,line))
    formulas={
      'macd_rsi60':'MACD12/26 crosses below EMA9 signal AND RSI14 crossed below60 on t,t-1,t-2',
      'macd_positive':'MACD12/26 crosses below EMA9 signal AND MACD>0',
      'cci100_up20':'CCI20 crosses below100 AND SMA20[t]>SMA20[t-5]',
      'rsi60':'Wilder RSI14 crosses below60',
      'stoch80':'Stochastic14/3/3 K crosses below80',
      'price5':'Close crosses below SMA5'}
    for key in BENCHMARKS:
        a=prior[:,priorids.index(key)].astype(float);a[a<0]=np.nan
        add(key,original.META[key]['label'],'Benchmark',formulas[key],a)
    # Original context uses RSI>=60. All seven covariates are observable today.
    return np.stack([np.where(np.isfinite(a),a,-1).astype(np.int8) for a in d.values()],1),list(d),ctx,atr,cv,aux
