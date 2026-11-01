"""Eleven predeclared new events and five unchanged benchmark events.

Inputs are one contiguous OHLCV/date segment. No retrospective labels enter.
Technical definitions and deliberate platform variations are in protocol.json.
"""
import numpy as np
from legacy import roll,lag,ema,wilder,ratio,cross,new_state

META={}
BENCHMARKS=['rsi30','cci-100','cci_recovery','macd_rsi40','price5']

def up(a,b):
    a=np.asarray(a,float)
    return cross(-a,-np.broadcast_to(b,a.shape))

def supertrend(h,l,c,period=10,multiplier=3):
    tr=np.maximum(h-l,np.maximum(abs(h-lag(c)),abs(l-lag(c))))
    atr=wilder(tr,period);basicup=(h+l)/2+multiplier*atr;basiclow=(h+l)/2-multiplier*atr
    upper=np.full(len(c),np.nan);lower=upper.copy();direction=upper.copy()
    for t in range(len(c)):
        if not np.isfinite(atr[t]):continue
        if not t or not np.isfinite(upper[t-1]):
            upper[t]=basicup[t];lower[t]=basiclow[t];direction[t]=-1;continue
        upper[t]=basicup[t] if basicup[t]<upper[t-1] or c[t-1]>upper[t-1] else upper[t-1]
        lower[t]=basiclow[t] if basiclow[t]>lower[t-1] or c[t-1]<lower[t-1] else lower[t-1]
        if direction[t-1]<0:direction[t]=1 if c[t]>upper[t] else -1
        else:direction[t]=-1 if c[t]<lower[t] else 1
    return direction,np.where(direction==1,lower,upper)

def psar(h,l,c,start=.02,increment=.02,maximum=.2):
    """Strict penetration, then prior-two-range clamp; close-based initialization."""
    n=len(c);sar=np.full(n,np.nan);direction=sar.copy()
    if n<2:return direction,sar
    bull=c[1]>c[0];sar[1]=l[0] if bull else h[0];ep=h[1] if bull else l[1];af=start;direction[1]=1 if bull else -1
    for t in range(2,n):
        s=sar[t-1]+af*(ep-sar[t-1])
        reverse=l[t]<s if bull else h[t]>s
        if reverse:
            s=ep;bull=not bull;ep=h[t] if bull else l[t];af=start
        else:
            s=min(s,l[t-1],l[t-2]) if bull else max(s,h[t-1],h[t-2])
            newep=max(ep,h[t]) if bull else min(ep,l[t])
            if newep!=ep:af=min(maximum,af+increment);ep=newep
        sar[t]=s;direction[t]=1 if bull else -1
    return direction,sar

def quarter_vwap(h,l,c,v,dates):
    """Daily typical-price proxy. Reset at known quarter boundary or segment start."""
    q=np.array([int(str(x)[:4])*4+(int(str(x)[5:7])-1)//3 for x in dates])
    out=np.full(len(c),np.nan);age=np.zeros(len(c),int);total=weight=0.;origin=0
    for t in range(len(c)):
        if not t or q[t]!=q[t-1]:total=weight=0.;origin=t
        total+=(h[t]+l[t]+c[t])/3*v[t];weight+=v[t];age[t]=t-origin
        if weight>0:out[t]=total/weight
    f=up(c,out);f[age<5]=np.nan
    return f,out,age

def calculate(z):
    c,o,h,l,v=[np.asarray(z[k],float) for k in ['close','open','high','low','volume']]
    n=len(c);d={};ma20=roll(c,20);ma5=roll(c,5)
    def add(key,label,family,formula,value):
        a=np.asarray(value,float).copy();a[:min(65,n)]=np.nan
        d[key]=a;META[key]=dict(id=key,label=label,family=family,kind='event',formula=formula)
    delta=c-lag(c);gain=wilder(np.maximum(delta,0),14);loss=wilder(np.maximum(-delta,0),14)
    rsi=100*ratio(gain,gain+loss);rsi[(gain+loss)==0]=50
    tr=np.maximum(h-l,np.maximum(abs(h-lag(c)),abs(l-lag(c))));atr=wilder(tr,14)
    ret=c/lag(c)-1;rv=ratio(v,lag(roll(v,20)))
    stdir,st=supertrend(h,l,c)
    add('supertrend','Supertrend bullish flip','Supertrend','Wilder ATR10 * 3 trailing bands; down-to-up flip at close',up(stdir,0))
    psdir,ps=psar(h,l,c)
    add('psar','Parabolic SAR reversal','SAR','PSAR start=.02, increment=.02, max=.20; bearish-to-bullish direction reversal',up(psdir,0))
    e3=ema(ema(ema(c,18),18),18);trix=100*(e3/lag(e3)-1);txsig=ema(trix,9)
    add('trix_zero','TRIX18 zero cross','TRIX','1-bar percent change of triple EMA18 crosses above0',up(trix,0))
    add('trix_signal','TRIX18 signal cross','TRIX','TRIX18 crosses above its EMA9',up(trix,txsig))
    sk=roll(100*ratio(rsi-roll(rsi,14,'min'),roll(rsi,14,'max')-roll(rsi,14,'min')),3);sd=roll(sk,3)
    add('stochrsi20','StochRSI K20 recovery','StochRSI','RSI14, range14, SMA3 K: K crosses20; flat range unknown',up(sk,20))
    add('stochrsi_cross','StochRSI low K/D cross','StochRSI','K crosses SMA3(K) and previous K<=20',up(sk,sd)*(lag(sk)<=20))
    dm=c-lag(c,5);gu=wilder(np.maximum(dm,0),20);gd=wilder(np.maximum(-dm,0),20)
    rmi=100*ratio(gu,gu+gd);rmi[(gu+gd)==0]=50
    for level in [30,50]:add('rmi'+str(level),'RMI20/5 '+str(level)+' recovery','RMI',f'Wilder20 smoothed 5-day changes: RMI crosses above{level}',up(rmi,level))
    mult=ratio(2*c-h-l,h-l);mult[h==l]=0;adl=np.cumsum(mult*v);chaikin=ema(adl,3)-ema(adl,10)
    add('chaikin','Chaikin3/10 zero cross','Chaikin','EMA3(ADL)-EMA10(ADL) crosses0; H=L contribution0',up(chaikin,0))
    vf,vwap,va=quarter_vwap(h,l,c,v,z['date'])
    add('avwap_quarter','Quarter daily AVWAP cross','AVWAP proxy','C crosses sum(TP*V)/sum(V) since calendar quarter/segment start; at least5 previous anchor bars',vf)
    vo=100*(ratio(roll(v,5),roll(v,20))-1)
    add('volume_osc','Volume oscillator + up day','Volume oscillator','SMA5(V)/SMA20(V)-1 crosses0 AND C>previous C',up(vo,0)*(ret>0))
    # Benchmarks retain the prior research's definitions and 65-bar mask.
    add('rsi30','RSI30 recovery','Benchmark','Wilder RSI14 crosses above30',up(rsi,30))
    tp=(h+l+c)/3;w=np.lib.stride_tricks.sliding_window_view(tp,20)
    mad=np.r_[np.full(19,np.nan),np.mean(abs(w-w.mean(1)[:,None]),1)];cci=ratio(tp-roll(tp,20),.015*mad)
    cc=up(cci,-100);add('cci-100','CCI -100 recovery','Benchmark','CCI20 crosses above-100',cc)
    add('cci_recovery','CCI recovery / falling MA20','Benchmark','CCI20 crosses-100 AND SMA20[t]<SMA20[t-5]',cc*(ma20<lag(ma20,5)))
    macd=ema(c,12)-ema(c,26);ms=ema(macd,9);r40=up(rsi,40);r40[:min(65,n)]=np.nan;recent=roll(r40,3,'max')
    add('macd_rsi40','MACD + recent RSI40','Benchmark','MACD12/26 crosses EMA9 signal AND RSI40 crossed on t,t-1,t-2',np.where(np.isfinite(recent),up(macd,ms)*(recent==1),np.nan))
    add('price5','Close crosses SMA5','Benchmark','C crosses above SMA5',up(c,ma5))
    ctx=np.column_stack([ma20>lag(ma20,5),c>ma20,rsi>=50]).astype(np.int8)
    cv=np.column_stack([atr/c,ret,c/lag(c,5)-1,c/lag(c,20)-1,c/ma20-1,rsi,rv])
    aux=dict(supertrend=st,st_direction=stdir,psar=ps,ps_direction=psdir,trix=trix,trix_signal=txsig,sk=sk,sd=sd,rmi=rmi,chaikin=chaikin,adl=adl,avwap=vwap,avwap_age=va,volume_osc=vo,rsi=rsi)
    return np.stack([np.where(np.isfinite(a),a,-1).astype(np.int8) for a in d.values()],1),list(d),ctx,atr,cv,aux
