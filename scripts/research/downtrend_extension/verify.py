"""Causality, independent scalar checks and pre-result frozen evidence."""
from study import *
from datetime import datetime,timezone

def sample(n=420,seed=71):
    rng=np.random.default_rng(seed);c=100*np.exp(np.cumsum(rng.normal(0,.025,n)))
    o=c*np.exp(rng.normal(0,.008,n));h=np.maximum(c,o)*(1+rng.uniform(.001,.03,n));l=np.minimum(c,o)*(1-rng.uniform(.001,.03,n))
    return dict(close=c,open=o,high=h,low=l,volume=rng.uniform(1000,100000,n),date=(np.datetime64('2019-01-01')+np.arange(n)).astype(str))

def synthetic():
    cells=bench=0
    for seed in [71,93]:
        z=sample(seed=seed);f,ids,ctx,atr,cv,aux=signals.calculate(z)
        for cut in [66,67,70,80,90,120,150,199,200,301,419]:
            ff=signals.calculate({k:v[:cut] for k,v in z.items()})[0]
            assert np.array_equal(ff,f[:cut]),('prefix',seed,cut);cells+=ff.size
        old,oi,oc,oa=signals.original.calculate(z)
        for k in signals.BENCHMARKS:
            assert np.array_equal(f[:,ids.index(k)],old[:,oi.index(k)]);bench+=len(f)
        assert np.array_equal(ctx,oc) and np.allclose(atr,oa,equal_nan=True)
        # Direct scalar window sums independently verify each confirmed pivot.
        expected=[];pivot=np.nan
        for t in range(len(f)):
            if t>=4:
                w=list(z['low'][t-4:t+1])
                if w[2]<w[0] and w[2]<w[1] and w[2]<w[3] and w[2]<w[4]:pivot=w[2]
            expected.append(pivot)
        assert np.allclose(expected,aux['fractal_low'],equal_nan=True)
        for t in range(65,len(f)):
            if np.isfinite(expected[t-1]):
                hit=z['close'][t]<expected[t] and z['close'][t-1]>=expected[t-1]
                assert f[t,ids.index('fractal_break')]==hit
        # All later prices may change without affecting earlier decisions.
        future={k:v.copy() for k,v in z.items()}
        for k in ['close','open','high','low']:future[k][250:]*=3
        assert np.array_equal(signals.calculate(future)[0][:250],f[:250])
    low=np.array([8,7,3,6,7,5,4,1,4,5.])
    expected=np.array([np.nan,np.nan,np.nan,np.nan,3,3,3,3,3,1.])
    assert np.allclose(signals.fractal_level(low),expected,equal_nan=True)
    slope=np.r_[.01,np.full(10,-.01),0.,np.full(4,-.01),.01];fit=np.r_[0,np.cumsum(slope)]
    lab=labels(fit,np.zeros(len(fit),int))
    assert lab['starts'].tolist()==[1,12] and lab['ends'].tolist()==[11,16]
    assert np.all(lab['cls'][1:7]==1) and np.all(lab['cls'][7:11]==2) and np.all(lab['cls'][12:16]==3)
    z=sample(150);z['segment']=np.zeros(150,int);a=forward(z);z['segment'][100:]=1;b=forward(z)
    assert np.isfinite(a[21][90]).all() and np.isnan(b[21][90]).all()
    # Imported upstream formula checks supplement, not replace, new event tests.
    receipt=dict(status='PASS',prefix_cells=cells,benchmark_cells=bench,fractal_right_bar_fixture=True,down_label_six_day_fixture=True,price_gap_fixture=True,utc=datetime.now(timezone.utc).isoformat())
    write(OUT/'verification-synthetic.json',receipt);print(receipt,flush=True)

def freeze():
    dest=OUT/'protocol-receipt.json';assert not dest.exists()
    paths=[p for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    paths += [ROOT/'scripts/research/uptrend_extension/signals.py',ROOT/'scripts/research/uptrend_extension/legacy.py',ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research/features.py']
    prior={str(p.relative_to(ROOT)):sha(p) for p in paths}
    receipt=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(Path(__file__).with_name('protocol.json')),signals_sha256=sha(Path(signals.__file__)),prior_files=prior,inventory_sha256=sha(OLD/'inventory.json'),new_market_results_exist=bool(list((OUT/'evaluate').glob('*.npz'))))
    assert not receipt['new_market_results_exist'];write(dest,receipt)
    write(ROOT/'docs/research/downtrend-extension-2026-10-29/protocol-receipt.json',receipt)
    print('Frozen before market outcomes',receipt['frozen_utc'],len(prior),flush=True)

if __name__=='__main__':synthetic() if len(sys.argv)==1 else freeze()
