"""Independent scalar values and hand-solvable trend-band fixture."""
from verify import sample
from study import *
from datetime import datetime,timezone

def scalar_ema(values,period):
    out=np.full(len(values),np.nan);state=None;count=0
    for i,v in enumerate(values):
        if not np.isfinite(v):continue
        state=float(v) if state is None else state+(v-state)*2/(period+1)
        count+=1
        if count>=period:out[i]=state
    return out

def main():
    z=sample();_,_,_,_,_,a=signals.calculate(z)
    triple=scalar_ema(scalar_ema(scalar_ema(z['close'],18),18),18)
    expected=np.r_[np.nan,100*(triple[1:]/triple[:-1]-1)]
    assert np.allclose(a['trix'],expected,equal_nan=True)
    assert np.allclose(a['trix_signal'],scalar_ema(expected,9),equal_nan=True)
    adl=[];total=0
    for c,h,l,v in zip(z['close'],z['high'],z['low'],z['volume']):
        total+=((c-l)-(h-c))/(h-l)*v;adl.append(total)
    assert np.allclose(a['adl'],adl)
    assert np.allclose(a['chaikin'],scalar_ema(adl,3)-scalar_ema(adl,10),equal_nan=True)
    for t in range(20,len(z['close'])):
        v=z['volume'];expected=100*((sum(v[t-4:t+1])/5)/(sum(v[t-19:t+1])/20)-1)
        assert np.isclose(a['volume_osc'][t],expected)
    c=np.r_[np.full(25,100.),np.full(10,110.),np.full(25,90.)]
    dr,band=signals.supertrend(c+1,c-1,c)
    assert np.isnan(dr[:10]).all() and np.all(dr[10:25]==-1)
    assert np.all(dr[25:35]==1) and np.all(dr[35:]==-1)
    assert band[24]==106 and np.isclose(band[25],101.3)
    # All decisions above are independent of the real-sample performance.
    result=dict(status='PASS',checks=['TRIX scalar recursive EMA and signal EMA','Chaikin signed range-location volume and scalar EMA','400 direct volume-oscillator windows','hand-solvable Supertrend jump/reversal'],completed_utc=datetime.now(timezone.utc).isoformat())
    write(ROOT/'docs/research/downtrend-extension-2026-10-29/verification-formulas.json',result);print(result,flush=True)

if __name__=='__main__':main()
