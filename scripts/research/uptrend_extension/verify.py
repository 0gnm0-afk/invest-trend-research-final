"""Synthetic causal/formula checks; immutable protocol and input lineage."""
from study import *
from datetime import datetime,timezone
import importlib.util,ast

def sample(n=420,seed=71):
    rng=np.random.default_rng(seed);c=100*np.exp(np.cumsum(rng.normal(0,.025,n)))
    o=c*np.exp(rng.normal(0,.008,n));h=np.maximum(c,o)*(1+rng.uniform(.001,.03,n));l=np.minimum(c,o)*(1-rng.uniform(.001,.03,n))
    dates=(np.datetime64('2019-01-01')+np.arange(n)).astype(str)
    return dict(close=c,open=o,high=h,low=l,volume=rng.uniform(1000,100000,n),date=dates)

def scalar_wilder(x,n):
    y=[np.nan]*len(x)
    for t in range(len(x)):
        if t and np.isfinite(y[t-1]):y[t]=(y[t-1]*(n-1)+x[t])/n
        elif t>=n-1 and all(np.isfinite(x[t-n+1:t+1])):y[t]=sum(x[t-n+1:t+1])/n
    return np.array(y)

def synthetic():
    cells=0;benchmark_cells=0;groups=0
    sys.path.insert(0,str(PRIOR/'scripts/downtrend_research'))
    spec=importlib.util.spec_from_file_location('original_up',PRIOR/'scripts/uptrend_confirmation/signals.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    for seed in [71,93]:
        z=sample(seed=seed);f,ids,ctx,atr,cv,a=signals.calculate(z)
        for cut in list(range(66,130))+[150,199,200,301,419]:
            ff=signals.calculate({k:v[:cut] for k,v in z.items()})[0]
            assert np.array_equal(ff,f[:cut]),('prefix',seed,cut)
            cells+=ff.size
        orig,oi,oc,oa,ov,aux=old.calculate(z)
        lookup={k:orig[:,j].astype(float) for j,k in enumerate(oi)}
        for k in lookup:lookup[k][lookup[k]<0]=np.nan
        recent=roll(lookup['rsi40'],3,'max')
        expected={'rsi30':lookup['rsi30'],'cci-100':lookup['cci-100'],'price5':lookup['price5'],'cci_recovery':lookup['cci-100']*(aux['ma20']<signals.lag(aux['ma20'],5)),'macd_rsi40':np.where(np.isfinite(recent),lookup['macd_signal']*(recent==1),np.nan)}
        for k,v in expected.items():
            v[:65]=np.nan;assert np.array_equal(f[:,ids.index(k)],np.where(np.isfinite(v),v,-1));benchmark_cells+=len(v)
        assert np.array_equal(ctx,oc) and np.allclose(atr,oa,equal_nan=True) and np.allclose(cv,ov,equal_nan=True)
        dm=np.r_[np.full(5,np.nan),z['close'][5:]-z['close'][:-5]]
        gu=scalar_wilder(np.maximum(dm,0),20);gd=scalar_wilder(np.maximum(-dm,0),20)
        assert np.allclose(a['rmi'],100*gu/(gu+gd),equal_nan=True)
        # AVWAP direct sums use only the current calendar quarter's dates.
        for t in [75,100,183,250,366,400]:
            q=lambda dt:str(dt)[:4]+'-'+str((int(str(dt)[5:7])-1)//3)
            ix=[j for j in range(t+1) if q(z['date'][j])==q(z['date'][t])]
            v=sum((z['high'][j]+z['low'][j]+z['close'][j])/3*z['volume'][j] for j in ix)/sum(z['volume'][j] for j in ix)
            assert np.isclose(v,a['avwap'][t])
        assert np.all(f[a['avwap_age']<5,ids.index('avwap_quarter')]==-1)
        groups+=4
    z=sample();z.update({k:np.full(420,100.) for k in ['close','open','high','low']})
    ff,ids,*_=signals.calculate(z);assert np.all(ff[65:,ids.index('stochrsi20')]==-1)
    h=np.array([11,10,9,8,12,13.]);l=h-2;c=h-1
    dr,sar=signals.psar(h,l,c)
    assert dr[1]==-1 and sar[1]==11 and np.isclose(sar[2],11) and np.isclose(sar[3],10.84) and dr[4]==1 and sar[4]==6
    # Scalar independent run scan and strict flat boundary.
    slope=np.r_[-.01,np.full(10,.01),0.,np.full(4,.01),-.01];fit=np.r_[0,np.cumsum(slope)];seg=np.zeros(len(fit),int)
    lab=labels(fit,seg);assert list(lab['starts'])==[1,12] and list(lab['ends'])==[11,16]
    assert np.all(lab['cls'][1:7]==1) and np.all(lab['cls'][7:11]==2) and np.all(lab['cls'][12:16]==3) and lab['cls'][0]==0
    z=sample(150);z['segment']=np.zeros(150,int);fut=forward(z);z['segment'][100:]=1;broken=forward(z)
    assert np.isfinite(fut[21][90]).all() and np.isnan(broken[21][90]).all()
    result=dict(status='PASS',prefix_cells=cells,benchmark_cells=benchmark_cells,synthetic_groups=groups+4,checked_utc=datetime.now(timezone.utc).isoformat())
    write(OUT/'verification-synthetic.json',result);print(result,flush=True)

def freeze():
    dest=OUT/'protocol-receipt.json';assert not dest.exists()
    files=list(PRIOR.rglob('*'));prior={str(p.relative_to(ROOT)):sha(p) for p in files if p.is_file() and '__pycache__' not in str(p)}
    receipt=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(Path(__file__).with_name('protocol.json')),signals_sha256=sha(Path(signals.__file__)),prior_files=prior,inventory_sha256=sha(OLD/'inventory.json'),new_market_results_exist=bool(list((OUT/'evaluate').glob('*.npz'))))
    assert not receipt['new_market_results_exist'];write(dest,receipt);write(ROOT/'docs/research/uptrend-extension-2026-10-29/protocol-receipt.json',receipt)
    print('Protocol frozen',receipt['frozen_utc'],len(prior),'prior files protected',flush=True)

if __name__=='__main__':synthetic() if len(sys.argv)==1 else freeze()
