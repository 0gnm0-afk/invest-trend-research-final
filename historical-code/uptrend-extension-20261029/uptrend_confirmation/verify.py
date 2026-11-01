"""Independent small checks before calculations; final artifact audit added later."""
from study import *
from datetime import datetime,timezone

def synthetic():
    # Finite preceding edge, a complete12-edge rise, flat, short3 rise, censored end.
    sl=np.r_[-.01,np.repeat(.01,12),0.,np.repeat(.02,3),-.01,np.repeat(.01,4)]
    fit=np.r_[0,np.cumsum(sl)];lab=labels(fit,np.zeros(len(fit),int))
    assert list(lab['starts'])==[1,14] and list(lab['ends'])==[13,17]
    assert list(np.flatnonzero(lab['cls']==1))==list(range(1,7))
    assert lab['cls'][0]==0 and lab['cls'][7]==2 and lab['cls'][15]==3 and not lab['known'][19]
    # Exact boundaries inclusive flat, numeric direction independently checked.
    tiny=np.array([-1e-6,0,1e-6,1.0001e-6,-1.0001e-6])
    assert np.array_equal((tiny>1e-6).astype(int)-(tiny<-1e-6).astype(int),[0,0,0,1,-1])
    base=np.zeros(12,int);base[2]=1;strong=np.zeros(12);strong[3:]=1;br=np.zeros(12);br[3]=1
    ex=extensions(base,strong,br)
    assert not ex[:,0].any() and list(np.flatnonzero(ex[:,1]))==[3] and list(np.flatnonzero(ex[:,2]))==[5]
    rng=np.random.default_rng(1023);c=100*np.exp(np.cumsum(rng.normal(0,.02,450)))
    z=dict(close=c,open=c*np.exp(rng.normal(0,.004,450)),high=c*1.03,low=c*.97,volume=rng.uniform(1e4,1e6,450))
    f,ids,ctx,atr,cv,_=signals.calculate(z);checked=0
    for cut in [80,101,149,201,301,400]:
        a=signals.calculate({k:v[:cut] for k,v in z.items()})
        assert np.array_equal(f[:cut],a[0]);assert np.allclose(cv[:cut],a[4],equal_nan=True);checked+=f[:cut].size
        zz=dict(z,segment=np.zeros(450,int));full,meta=signals.extras(zz,f,ids,['macd_signal','rsi40'])
        zz2={k:v[:cut] for k,v in zz.items()};part,_=signals.extras(zz2,f[:cut],ids,['macd_signal','rsi40'])
        assert np.array_equal(full[:cut],part)
    # Direct moving-average crossing independently of helper.
    for k in [5,20,200]:
        ma=np.array([c[t-k+1:t+1].mean() if t>=k-1 else np.nan for t in range(len(c))])
        for t in range(max(65,k),len(c)):
            tol=1e-12*max(abs(c[t]),abs(ma[t]));ptol=1e-12*max(abs(c[t-1]),abs(ma[t-1]))
            expected=int(c[t]-ma[t]>tol and c[t-1]-ma[t-1]<=ptol)
            assert f[t,ids.index(f'price{k}')]==expected
    # Independent Wilder seed/recursion; no use of indicator helper.
    rr=np.full(len(c),np.nan);g=np.maximum(np.diff(c),0);loss=np.maximum(-np.diff(c),0)
    avgg=g[:14].mean();avgl=loss[:14].mean();rr[14]=100*avgg/(avgg+avgl)
    for t in range(15,len(c)):
        avgg=(13*avgg+g[t-1])/14;avgl=(13*avgl+loss[t-1])/14;rr[t]=100*avgg/(avgg+avgl)
    assert np.allclose(rr[14:],cv[14:,5])
    for q in [30,40,50,60]:
        for t in range(65,len(c)):
            tol=1e-12*max(abs(rr[t]),q);ptol=1e-12*max(abs(rr[t-1]),q)
            assert f[t,ids.index(f'rsi{q}')]==int(rr[t]-q>tol and rr[t-1]-q<=ptol)
    zz=dict(z,segment=np.zeros(450,int));pp=forward(zz)
    for t in [65,123,280]:
        for h in [5,21,63]:
            assert np.allclose(pp[h][t],[c[t+h]/z['open'][t+1]-1,min(z['low'][t+1:t+h+1])/z['open'][t+1]-1,max(z['high'][t+1:t+h+1])/z['open'][t+1]-1])
    zz['segment'][200:]=1;pp=forward(zz);assert np.isnan(pp[21][190]).all()
    # A signal before onset remains a false onset confirmation, not removed.
    mask=np.array([1,1,1,0,0,0,0,1]+[0]*(len(fit)-8));idx=np.flatnonzero(mask)
    assert (lab['cls'][idx]==1).sum()/len(idx)==.5
    from infer import weights,classify
    assert (weights(np.random.default_rng(7),100,30,3).sum(1)==30).all()
    a=np.zeros((1,20));a[0,:10]=[100,10,4,2,1,8,42,1,49,3];a[0,10:]=[10,4,0,1,1,1,1,0,.2,4]
    pp,bb,mm=classify(a);assert np.allclose(pp,[[.4,.6,.7]]) and np.allclose(bb,[[.08,.5,.51]]) and np.isclose(mm[0,0],.4)
    ns=2;yc=np.array([[0.,.1],[.2,.3],[.4,.5]]);mean=yc.mean(0);correction=ns/len(yc)*(yc-mean)
    assert np.allclose(correction.sum(0),0)
    eps=1e-6;ww=np.array([1+eps,1,1]);finite=(ns*(ww@yc/ww.sum())-ns*mean)/eps
    assert np.allclose(finite,correction[0],atol=1e-6)
    result=dict(status='PASS',prefix_cells=checked,singles=len(ids),synthetic_groups=9,checked_utc=datetime.now(timezone.utc).isoformat())
    OUT.mkdir(exist_ok=True);write(OUT/'verification-synthetic.json',result);print(result)

def freeze():
    OUT.mkdir(exist_ok=True);doc=ROOT/'docs/uptrend-confirmation-2026-10-23';doc.mkdir(exist_ok=True)
    target=OUT/'protocol-receipt.json';assert not target.exists()
    prior={}
    for directory in ['scripts/downtrend_research','scripts/downtrend_confirmation','docs/downtrend-indicators-2026-10-21','docs/downtrend-confirmation-2026-10-21','docs/downtrend-closure-2026-10-22']:
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and '__pycache__' not in str(p):prior[str(p.relative_to(ROOT))]=sha(p)
    for name in ['downtrend-indicators-2026-10-21','downtrend-confirmation-2026-10-21','downtrend-closure-2026-10-22']:
        p=ROOT/'docs'/f'{name}.md';prior[str(p.relative_to(ROOT))]=sha(p)
    p=Path(__file__).with_name('protocol.json');receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(p),literature_sha256=sha(doc/'literature.md'),singles=BASE,prior_files=prior,inventory_sha256=sha(OLD/'inventory.json'),test_results_exist=False)
    write(target,receipt);write(doc/'protocol-receipt.json',receipt);write(doc/'protocol.json',json.loads(p.read_bytes()));print('frozen',len(BASE),'singles',len(prior),'prior files')

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='freeze':freeze()
    else:synthetic()
