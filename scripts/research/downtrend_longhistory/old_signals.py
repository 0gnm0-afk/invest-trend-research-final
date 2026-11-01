"""Causal, fixed-parameter daily events. Missing is -1, never a false signal."""
import numpy as np
import pandas as pd

def roll(x, n, how='mean'):
    return getattr(pd.Series(x).rolling(n), how)().to_numpy()

def lag(x, n=1):
    return np.r_[np.full(min(n,len(x)),np.nan),x[:-n]] if n<len(x) else np.full(len(x),np.nan)

def ema(x,n):
    return pd.Series(x).ewm(span=n,adjust=False,min_periods=n).mean().to_numpy()

def wilder(x,n):
    out=np.full(len(x),np.nan)
    for i in range(n-1,len(x)):
        if i and np.isfinite(out[i-1]):out[i]=(out[i-1]*(n-1)+x[i])/n
        elif np.isfinite(x[i-n+1:i+1]).all():out[i]=np.mean(x[i-n+1:i+1])
    return out

def ratio(a,b):
    return np.divide(a,b,out=np.full(np.broadcast(a,b).shape,np.nan),where=np.isfinite(b)&(b!=0))

def cross(a,b):
    a=np.asarray(a);b=np.broadcast_to(b,a.shape)
    tol=1e-12*np.maximum(abs(a),abs(b));diff=a-b
    ok=np.isfinite(a)&np.isfinite(b)&np.isfinite(lag(a))&np.isfinite(lag(b))
    return np.where(ok,(diff < -tol)&(lag(diff)>=-lag(tol)),np.nan)

def new_state(x):
    return np.where(np.isfinite(x)&np.isfinite(lag(x)),(x==1)&(lag(x)!=1),np.nan)

# id: Korean label, family. Controls remain visible but cannot enter shortlist.
META={}
def calculate(z):
    c,o,h,l,v=[np.asarray(z[k],float) for k in ['close','open','high','low','volume']]
    n=len(c);d={};ma={k:roll(c,k) for k in [5,10,20,50,60,200]}
    def add(key,label,family,value,valid=None):
        a=np.asarray(value,float).copy()
        if valid is not None:a[~valid]=np.nan
        a[:min(65,n)]=np.nan
        d[key]=a;META[key]={'label':label,'family':family}
    pc=lag(c);ret=c/pc-1
    up20=ma[20]>lag(ma[20],5)
    for k in [5,10,20,50,60,200]:
        add(f'price{k}',f'종가 {k}일선 신규 이탈','control' if k in [5,10] else 'MA',cross(c,ma[k]))
    for a,b in [(5,10),(5,20),(10,20),(20,60),(50,200)]:
        add(f'ma{a}_{b}',f'{a}/{b} 데드크로스','MA',cross(ma[a],ma[b]))
    add('price5_up20','5일선 이탈·20일선 상승','control',d['price5']*up20)
    add('ma510_up20','5/10 데드·20일선 상승','MA',d['ma5_10']*up20)
    add('ma510_early','5/10 데드·10일선>20일선','MA',d['ma5_10']*(ma[10]>ma[20]))
    add('requested','5/10 데드·종가<20일선·10일선>20일선','MA',d['ma510_early']*(c<ma[20]))
    add('price20_early','20일선 이탈·10일선>20일선','MA',d['price20']*(ma[10]>ma[20]))
    add('ma20_turn','20일선 5일 기울기 음전환','MA',new_state((ma[20]<lag(ma[20],5)).astype(float)))
    delta=c-pc;gain=wilder(np.maximum(delta,0),14);loss=wilder(np.maximum(-delta,0),14)
    rsi=100*ratio(gain,gain+loss);rsi[(gain+loss)==0]=50
    for q in [70,60,50,40]:add(f'rsi{q}',f'RSI14 {q} 하향 돌파','RSI',cross(rsi,q))
    macd=ema(c,12)-ema(c,26);sig=ema(macd,9)
    add('macd_signal','MACD 시그널 하향 교차','MACD',cross(macd,sig))
    add('macd_positive','MACD 양수권 시그널 하향 교차','MACD',d['macd_signal']*(macd>0))
    add('macd_zero','MACD 0선 하향 교차','MACD',cross(macd,0))
    tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)));atr=wilder(tr,14)
    up=h-lag(h);dn=lag(l)-l
    plus=wilder(np.where((up>dn)&(up>0),up,0.),14);minus=wilder(np.where((dn>up)&(dn>0),dn,0.),14)
    dx=100*ratio(abs(plus-minus),plus+minus);adx=wilder(dx,14)
    add('dmi_cross','DMI -DI가 +DI 상향 교차','DMI',cross(plus,minus))
    add('dmi_adx25','DMI 하락 교차·ADX≥25','DMI',d['dmi_cross']*(adx>=25),np.isfinite(adx))
    add('adx_bear_rising','-DI 우위·ADX20 상향 진입','DMI',cross(np.full(n,20.),adx)*(minus>plus))
    slowk=roll(100*ratio(c-roll(l,14,'min'),roll(h,14,'max')-roll(l,14,'min')),3);slowd=roll(slowk,3)
    add('stoch80','스토캐스틱(14,3,3) K 80 이탈','Stochastic',cross(slowk,80))
    add('stoch_high_cross','스토캐스틱 K/D 데드·전일 K≥80','Stochastic',cross(slowk,slowd)*(lag(slowk)>=80))
    tp=(h+l+c)/3;tm=roll(tp,20)
    windows=np.lib.stride_tricks.sliding_window_view(tp,20)
    mad=np.r_[np.full(19,np.nan),np.mean(abs(windows-windows.mean(axis=1)[:,None]),axis=1)]
    cci=ratio(tp-tm,.015*mad)
    for q in [100,0,-100]:add(f'cci{q}',f'CCI20 {q} 하향 돌파','CCI',cross(cci,q))
    sd=pd.Series(c).rolling(20).std(ddof=0).to_numpy();upper=ma[20]+2*sd;lower=ma[20]-2*sd
    add('bb_upper_reentry','볼린저 상단 밴드 안으로 복귀','Bollinger',cross(c,upper))
    add('bb_lower','볼린저 하단 신규 이탈','Bollinger',cross(c,lower))
    width=ratio(upper-lower,ma[20]);squeeze=lag(width)<=lag(roll(width,120,'min'))*1.1
    add('bb_squeeze_down','밴드 수축 뒤 하단 이탈','Bollinger',d['bb_lower']*squeeze,np.isfinite(lag(roll(width,120,'min'))))
    add('keltner_lower','EMA20−2ATR14 하단 이탈','ATR',cross(c,ema(c,20)-2*atr))
    for k in [20,60]:add(f'low{k}',f'직전 {k}일 저가 이탈 첫날','Price',new_state((c<lag(roll(l,k,'min'))).astype(float)))
    oldhi=lag(roll(h,20,'max'))
    add('failed_breakout20','20일 고가 돌파 실패·음봉','Price',new_state(((h>oldhi)&(c<oldhi)&(c<o)).astype(float)))
    add('bear_gap','전일 저가 아래 갭·음봉','Price',((o<lag(l))&(c<o)).astype(float))
    add('bear_engulf','전일 양봉을 감싼 음봉 몸통','Candle',((lag(c)>lag(o))&(c<o)&(o>=lag(c))&(c<=lag(o))).astype(float))
    add('upper_wick','윗꼬리≥60%·종가 하위30%','Candle',((ratio(h-np.maximum(o,c),h-l)>=.6)&(ratio(c-l,h-l)<=.3)).astype(float),h>l)
    relvol=ratio(v,lag(roll(v,20)))
    add('down_volume15','하락일·거래량 전20일의1.5배','Volume',new_state(((ret<0)&(relvol>=1.5)).astype(float)),np.isfinite(relvol))
    add('atr_drop_volume','전일 종가−1.5ATR 이탈·거래량1.5배','Volume',((c<pc-1.5*lag(atr))&(relvol>=1.5)).astype(float),np.isfinite(relvol)&np.isfinite(lag(atr)))
    flow=ratio(roll(v*np.sign(ret),20,'sum'),roll(v,20,'sum'))
    add('obv_outflow','20일 OBV 순유출 비율 −20% 진입','Volume',cross(flow,-.2))
    cmf=ratio(roll(np.nan_to_num(ratio(2*c-h-l,h-l))*v,20,'sum'),roll(v,20,'sum'))
    add('cmf_zero','CMF20 0선 하향 돌파','Volume',cross(cmf,0))
    add('cmf_minus10','CMF20 −0.1 하향 돌파','Volume',cross(cmf,-.1))
    mf=tp*v;positive=roll(np.where(tp>lag(tp),mf,0),14,'sum');negative=roll(np.where(tp<lag(tp),mf,0),14,'sum')
    mfi=100*ratio(positive,positive+negative)
    mfi[roll(np.isfinite(v).astype(float),14,'min')!=1]=np.nan
    for q in [80,50]:add(f'mfi{q}',f'MFI14 {q} 하향 돌파','Volume',cross(mfi,q))
    roc=c/lag(c,10)-1
    add('roc10_zero','10일 ROC 음전환','Momentum',cross(roc,0))
    hw=np.lib.stride_tricks.sliding_window_view(h,25);lw=np.lib.stride_tricks.sliding_window_view(l,25)
    aup=np.r_[np.full(24,np.nan),100*(24-np.argmax(hw[:,::-1],axis=1))/24]
    adn=np.r_[np.full(24,np.nan),100*(24-np.argmin(lw[:,::-1],axis=1))/24]
    add('aroon_cross','Aroon25 하락 교차','Aroon',cross(aup,adn))
    vmplus=roll(abs(h-lag(l)),14,'sum');vmminus=roll(abs(l-lag(h)),14,'sum')
    add('vortex_cross','Vortex14 하락 교차','Vortex',cross(vmplus,vmminus))
    tenkan=(roll(h,9,'max')+roll(l,9,'min'))/2;kijun=(roll(h,26,'max')+roll(l,26,'min'))/2
    add('ichimoku_tk','일목 전환선/기준선 데드','Ichimoku',cross(tenkan,kijun))
    add('ichimoku_base','일목 기준선 종가 이탈','Ichimoku',cross(c,kijun))
    cloudtop=np.maximum(lag((tenkan+kijun)/2,26),lag((roll(h,52,'max')+roll(l,52,'min'))/2,26))
    cloudbottom=np.minimum(lag((tenkan+kijun)/2,26),lag((roll(h,52,'max')+roll(l,52,'min'))/2,26))
    add('ichimoku_cloud','당일에 표시된 일목 구름 하단 이탈','Ichimoku',cross(c,cloudbottom))
    volratio=ratio(pd.Series(np.log(c/pc)).rolling(5).std().to_numpy(),pd.Series(np.log(c/pc)).rolling(20).std().to_numpy())
    add('vol_expansion','5일/20일 변동성1.25배 신규 진입','Volatility',cross(np.full(n,1.25),volratio))
    add('macd_rsi60','MACD 데드·최근3일 RSI60 이탈','Combination',d['macd_signal']*(roll(d['rsi60'],3,'max')==1))
    add('stoch_macd','스토캐스틱80 이탈·MACD<시그널','Combination',d['stoch80']*(macd<sig))
    add('cci100_up20','CCI100 이탈·20일선 상승','Combination',d['cci100']*up20)
    add('bb_rsi60','밴드 상단 복귀·RSI<60','Combination',d['bb_upper_reentry']*(rsi<60))
    add('macd_volume','MACD 데드·거래량1.5배','Combination',d['macd_signal']*(relvol>=1.5),np.isfinite(relvol))
    add('low20_volume','20일 저가 이탈·거래량1.5배','Combination',d['low20']*(relvol>=1.5),np.isfinite(relvol))
    add('rsi_divergence','20일 종가 신고가·이전 고점 RSI보다5 낮음','Divergence',np.zeros(n))
    for t in range(66,n):
        j=t-20+int(np.argmax(c[t-20:t]))
        d['rsi_divergence'][t]=float(c[t]>c[j] and rsi[t]<rsi[j]-5)
    # All context variables use only current or earlier observations.
    ctx=np.column_stack([up20, c>ma[20], rsi>=60]).astype(np.int8)
    return np.stack([np.where(np.isfinite(a),a,-1).astype(np.int8) for a in d.values()],axis=1),list(d),ctx,atr
