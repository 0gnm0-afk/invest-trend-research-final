"""Fixed causal upside events; no labels or future bars are accepted here.

Reuses the inherited numerical primitives (EMA, Wilder, crossing tolerance).
Additional recovery/pivot candidates are not transformations of bearish flags.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'downtrend_research'))
import numpy as np
import pandas as pd
from legacy import roll,lag,ema,wilder,ratio,cross,new_state

META={}
def up(a,b):
    a=np.asarray(a,float);return cross(-a,-np.broadcast_to(b,a.shape))

def calculate(z):
    c,o,h,l,v=[np.asarray(z[k],float) for k in ['close','open','high','low','volume']]
    n=len(c);d={};ma={k:roll(c,k) for k in [5,10,20,50,60,200]}
    def add(key,family,formula,value,kind='event'):
        a=np.asarray(value,float).copy();a[:min(65,n)]=np.nan
        d[key]=a;META[key]=dict(id=key,label=key.replace('_',' '),family=family,kind=kind,formula=formula)
    for k in [5,10,20,50,200]:add(f'price{k}','control' if k<=10 else 'MA',f'C crosses above SMA{k}',up(c,ma[k]))
    for a,b in [(5,10),(5,20),(10,20),(20,60),(50,200)]:add(f'ma{a}_{b}','MA',f'SMA{a} crosses above SMA{b}',up(ma[a],ma[b]))
    add('ma20_turn','MA','SMA20[t]>SMA20[t-5], first true day',new_state(np.where(np.isfinite(lag(ma[20],5)),ma[20]>lag(ma[20],5),np.nan)))
    delta=c-lag(c);gain=wilder(np.maximum(delta,0),14);loss=wilder(np.maximum(-delta,0),14)
    rsi=100*ratio(gain,gain+loss);rsi[(gain+loss)==0]=50
    for q in [30,40,50,60]:add(f'rsi{q}','RSI',f'Wilder RSI14 crosses above {q}',up(rsi,q))
    macd=ema(c,12)-ema(c,26);sig=ema(macd,9)
    add('macd_signal','MACD','EMA12(C)-EMA26(C) crosses above EMA9(MACD)',up(macd,sig))
    add('macd_zero','MACD','MACD crosses above 0',up(macd,0))
    tr=np.maximum(h-l,np.maximum(abs(h-lag(c)),abs(l-lag(c))));atr=wilder(tr,14)
    uh=h-lag(h);dl=lag(l)-l
    plus=wilder(np.where((uh>dl)&(uh>0),uh,0),14);minus=wilder(np.where((dl>uh)&(dl>0),dl,0),14)
    adx=wilder(100*ratio(abs(plus-minus),plus+minus),14)
    add('dmi_cross','DMI','Wilder14 +DM crosses above -DM (common ATR denominator)',up(plus,minus))
    add('adx_bull','DMI','ADX14 crosses above20 while +DM>-DM',up(adx,20)*(plus>minus))
    k=roll(100*ratio(c-roll(l,14,'min'),roll(h,14,'max')-roll(l,14,'min')),3);kd=roll(k,3)
    add('stoch20','Stochastic','Slow K=SMA3(100*(C-min L14)/(max H14-min L14)) crosses above20',up(k,20))
    add('stoch_low_cross','Stochastic','K crosses above SMA3(K), previous K<=20',up(k,kd)*(lag(k)<=20))
    tp=(h+l+c)/3;windows=np.lib.stride_tricks.sliding_window_view(tp,20)
    mad=np.r_[np.full(19,np.nan),np.mean(abs(windows-windows.mean(1)[:,None]),1)]
    cci=ratio(tp-roll(tp,20),.015*mad)
    for q in [-100,0,100]:add(f'cci{q}','CCI',f'(TP-SMA20(TP))/(.015*mean absolute deviation20) crosses above {q}',up(cci,q))
    sd=pd.Series(c).rolling(20).std(ddof=0).to_numpy();upper=ma[20]+2*sd;lower=ma[20]-2*sd
    add('bb_reentry','Bollinger','C crosses above SMA20-2*population SD20',up(c,lower))
    add('bb_upper','Bollinger','C crosses above SMA20+2*population SD20',up(c,upper))
    width=ratio(upper-lower,ma[20]);oldmin=lag(roll(width,120,'min'))
    add('bb_squeeze','Bollinger','bb_upper AND previous bandwidth<=1.1*previous120 minimum bandwidth',np.where(np.isfinite(oldmin),d['bb_upper']*(lag(width)<=oldmin*1.1),np.nan))
    add('keltner_upper','ATR','C crosses above EMA20+2*Wilder ATR14',up(c,ema(c,20)+2*atr))
    for q in [20,60]:
        level=lag(roll(h,q,'max'));state=np.where(np.isfinite(level),c>level,np.nan)
        add(f'high{q}','Price',f'C>maximum H of prior{q} bars, first true day',new_state(state))
    oldlow=lag(roll(l,20,'min'))
    add('failed_low20','Price','L<prior20 minimum L AND C>that level AND C>O, first true day',new_state(np.where(np.isfinite(oldlow),(l<oldlow)&(c>oldlow)&(c>o),np.nan)))
    add('bull_gap','Candle','O>previous H AND C>O; every qualifying day',np.where(np.isfinite(lag(h)),(o>lag(h))&(c>o),np.nan))
    add('bull_engulf','Candle','previous C<O, C>O, O<=previous C and C>=previous O; every qualifying day',np.where(np.isfinite(lag(o)),(lag(c)<lag(o))&(c>o)&(o<=lag(c))&(c>=lag(o)),np.nan))
    ret=c/lag(c)-1;rv=ratio(v,lag(roll(v,20)))
    add('up_volume15','Volume','C>previous C AND V/prior20 mean V>=1.5, first true day',new_state(np.where(np.isfinite(rv),(ret>0)&(rv>=1.5),np.nan)))
    add('atr_jump_volume','Volume','C>previous C+1.5*previous ATR14 AND relative volume>=1.5; every qualifying day',np.where(np.isfinite(lag(atr))&np.isfinite(rv),(c>lag(c)+1.5*lag(atr))&(rv>=1.5),np.nan))
    flow=ratio(roll(v*np.sign(ret),20,'sum'),roll(v,20,'sum'))
    add('obv_inflow','Volume','sum20(V*sign(return1))/sum20(V) crosses above .2',up(flow,.2))
    cmf=ratio(roll(np.nan_to_num(ratio(2*c-h-l,h-l))*v,20,'sum'),roll(v,20,'sum'))
    add('cmf_zero','Volume','CMF20 crosses above0; H=L contribution0',up(cmf,0))
    mf=tp*v;pos=roll(np.where(tp>lag(tp),mf,0),14,'sum');neg=roll(np.where(tp<lag(tp),mf,0),14,'sum');mfi=100*ratio(pos,pos+neg)
    for q in [20,50]:add(f'mfi{q}','Volume',f'MFI14 crosses above{q}',up(mfi,q))
    add('roc10_zero','Momentum','C/C[t-10]-1 crosses above0',up(c/lag(c,10)-1,0))
    hw=np.lib.stride_tricks.sliding_window_view(h,25);lw=np.lib.stride_tricks.sliding_window_view(l,25)
    au=np.r_[np.full(24,np.nan),100*(24-np.argmax(hw[:,::-1],1))/24];ad=np.r_[np.full(24,np.nan),100*(24-np.argmin(lw[:,::-1],1))/24]
    add('aroon_cross','Aroon','AroonUp25 crosses above AroonDown25; ties most recent',up(au,ad))
    add('vortex_cross','Vortex','sum14(abs(H-prev L)) crosses above sum14(abs(L-prev H))',up(roll(abs(h-lag(l)),14,'sum'),roll(abs(l-lag(h)),14,'sum')))
    ten=(roll(h,9,'max')+roll(l,9,'min'))/2;kij=(roll(h,26,'max')+roll(l,26,'min'))/2
    cloud=np.maximum(lag((ten+kij)/2,26),lag((roll(h,52,'max')+roll(l,52,'min'))/2,26))
    add('ichimoku_tk','Ichimoku','9-bar midpoint crosses above26-bar midpoint',up(ten,kij))
    add('ichimoku_cloud','Ichimoku','C crosses above max of both cloud spans calculated26 bars earlier',up(c,cloud))
    trough=roll(l,20,'min');add('rebound2atr','Recovery','(C-min L20)/ATR14 crosses above2',up(ratio(c-trough,atr),2))
    # A pivot at k is only available at k+2. Its right wing never uses future t.
    pivot=np.full(n,np.nan);last=np.nan
    for t in range(4,n):
        j=t-2
        if h[j]>h[j-2:j].max() and h[j]>=h[j+1:t+1].max():last=h[j]
        pivot[t]=last
    add('pivot_break','Structure','C crosses above latest 5-bar pivot high, known only2 bars after pivot; left strict/right inclusive',up(c,pivot))
    priorhigh=lag(roll(c,63,'max'));recovery=(lag(c)/priorhigh-1)<=-.10
    add('reclaim_drawdown','Recovery','price20 AND previous close<=90% of preceding63 close maximum',np.where(np.isfinite(priorhigh),d['price20']*recovery,np.nan))
    ctx=np.column_stack([ma[20]>lag(ma[20],5),c>ma[20],rsi>=50]).astype(np.int8)
    cv=np.column_stack([atr/c,ret,c/lag(c,5)-1,c/lag(c,20)-1,c/ma[20]-1,rsi,rv])
    aux=dict(macd=macd,signal=sig,rsi=rsi,ma20=ma[20],ma5=ma[5],relative_volume=rv,cci=cci)
    return np.stack([np.where(np.isfinite(a),a,-1).astype(np.int8) for a in d.values()],1),list(d),ctx,atr,cv,aux

def extras(z,base,ids,selected):
    """Small frozen follow-up family and explicit maintained-state comparators."""
    from study import extensions
    f=base.copy();meta=[META[k].copy() for k in ids];n=len(f)
    extra_ids=['macd_rsi40','macd_negative','high20_volume','cci_recovery']
    forms=['macd_signal AND rsi40 crossed upward on t,t-1 or t-2','macd_signal AND MACD<0','high20 AND relative_volume>=1.5','cci-100 AND SMA20[t]<SMA20[t-5]']
    values=np.full((n,4+3*len(selected)+4),-1,np.int8)
    for g in np.unique(z['segment']):
        ix=np.flatnonzero(z['segment']==g)
        if len(ix)<80:continue
        zz={k:z[k][ix] for k in ['close','open','high','low','volume']};ff,_,_,_,_,a=calculate(zz)
        lookup={k:ff[:,j].astype(float) for j,k in enumerate(ids)}
        for k in lookup:lookup[k][lookup[k]<0]=np.nan
        recent=roll(lookup['rsi40'],3,'max')
        out=[np.where(np.isfinite(recent),lookup['macd_signal']*(recent==1),np.nan),lookup['macd_signal']*(a['macd']<0),lookup['high20']*(a['relative_volume']>=1.5),lookup['cci-100']*(a['ma20']<lag(a['ma20'],5))]
        strong=np.where(np.isfinite(a['ma20']),zz['close']>a['ma20'],np.nan)
        for key in selected:
            ex=extensions(ff[:,ids.index(key)],strong,up(zz['close'],a['ma20'])).astype(float);ex[ex<0]=np.nan
            out.extend(ex.T)
        out.extend([np.where(np.isfinite(a['ma5']),zz['close']>a['ma5'],np.nan),strong,np.where(np.isfinite(a['signal']),a['macd']>a['signal'],np.nan),np.where(np.isfinite(a['signal'])&np.isfinite(a['rsi']),(a['macd']>a['signal'])&(a['rsi']>40),np.nan)])
        arr=np.stack(out,1);arr[:65]=np.nan;values[ix]=np.where(np.isfinite(arr),arr,-1).astype(np.int8)
    for k,form in zip(extra_ids,forms):meta.append(dict(id=k,label=k.replace('_',' '),family='Anchor',kind='event',formula=form))
    for key in selected:
        for tag,form in [('and20','base event AND C>SMA20 on same day'),('then20','first price20 event base day..+5 inclusive'),('persist3','first three consecutive C>SMA20, run starts>=base and completes<=base+5')]:meta.append(dict(id=key+'__'+tag,label=key+' '+tag,family='Follow-up',kind='event',base=key,formula=form))
    for key,form in [('state_price5','C>SMA5'),('state_price20','C>SMA20'),('state_macd','MACD>signal'),('state_macd_rsi40','MACD>signal AND RSI>40')]:meta.append(dict(id=key,label=key.replace('_',' '),family='State',kind='state',formula=form+'; every qualifying day'))
    return np.column_stack([f,values]),meta
