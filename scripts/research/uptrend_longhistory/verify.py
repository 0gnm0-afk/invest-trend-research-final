"""Direct causal, boundary, lineage and aggregate reconciliation checks."""
from study import *
from datetime import datetime,timezone

def sample(n=360,seed=71):
    rng=np.random.default_rng(seed);c=100*np.exp(np.cumsum(rng.normal(0,.025,n)))
    o=c*np.exp(rng.normal(0,.008,n));h=np.maximum(c,o)*(1+rng.uniform(.001,.03,n));l=np.minimum(c,o)*(1-rng.uniform(.001,.03,n))
    return dict(close=c,open=o,high=h,low=l,volume=rng.uniform(1000,100000,n),date=(np.datetime64('2019-01-01')+np.arange(n)).astype(str),segment=np.zeros(n,int))

def preliminary():
    prefix=0;shared=0
    for market in ['KR','US']:
        for seed in [71,93]:
            z=sample(seed=seed);f,meta,*_=features.calculate(z,market);ids=[b['id'] for b in meta]
            for cut in [80,99,130,199,200,251,359]:
                ff,*_=features.calculate({k:v[:cut] for k,v in z.items()},market)
                assert np.array_equal(ff,f[:cut]),(market,seed,cut)
                prefix+=ff.size
            nf,ni,*_=new_signals.calculate(z)
            for key in ni:
                assert np.array_equal(nf[:,ni.index(key)],f[:,ids.index(key)]),(market,seed,key)
                shared+=len(f)
    slope=np.r_[-.01,np.full(10,.01),0.,np.full(4,.01),-.01]
    z=np.r_[0,np.cumsum(slope)];lab=labels(z,np.zeros(len(z),int))
    assert list(lab['starts'])==[1,12] and list(lab['ends'])==[11,16]
    assert list(lab['cls'][1:11])==[1]*6+[2]*4 and list(lab['cls'][12:16])==[3]*4
    # Persistence signals on completion day, not retrospective first day.
    base=np.zeros(12,int);base[3]=1;weak=np.zeros(12);weak[4:8]=1;break20=np.zeros(12);break20[4]=1
    ex=extensions(base,weak,break20)
    assert np.flatnonzero(ex[:,1]).tolist()==[4] and np.flatnonzero(ex[:,2]).tolist()==[6]
    assert list(PERIODS[0][2:])==['2010-10-01','2025-09-30'] and M==180
    receipt=dict(prefix_cells=prefix,shared_extension_cells=shared,label_boundary='PASS',confirmation_clock='PASS',conditions={m:len(features.metadata(m)) for m in ['KR','US']},finished_utc=datetime.now(timezone.utc).isoformat())
    write(OUT/'verification-preliminary.json',receipt);print(receipt)

def final():
    protected=json.loads((INPUT/'protocol-receipt.json').read_bytes())
    for path,digest in protected['prior_files'].items():assert sha(ROOT/path)==digest,('protected prior file changed',path)
    assert sha(ROOT/'scripts/research/uptrend_extension/signals.py')==protected['signals_sha256']
    assert sha(ROOT/'scripts/research/uptrend_extension/protocol.json')==protected['protocol_sha256']
    assert sha(OLD/'inventory.json')==protected['inventory_sha256']
    rr=records();usable=0;reconciled=0;checked=0;totals={m:np.zeros((3,72,len(COLS))) for m in ['KR','US']};inherited={m:np.zeros((72,len(COLS))) for m in ['KR','US']};eps={m:np.zeros((72,10)) for m in ['KR','US']}
    allsources=[]
    for rec in rr:
        p=Path(rec['cache_path']);dest=OUT/'evaluate'/p.name
        if not p.exists():assert not dest.exists();continue
        mm=json.loads(p.with_suffix('.json').read_bytes());assert sha(p)==mm['cache_sha256'];usable+=1
        allsources.append(dict(market=rec['market'],symbol=rec['symbol'],group=rec.get('research_source_group','inherited'),path=str(p),sha256=sha(p)))
        assert dest.exists(),p.name
        with np.load(dest) as q:
            a=q['totals'];e=q['episodes'];months=q['months'];cells=q['cells']
            assert np.allclose(cells.sum(0),a[0],rtol=1e-12,atol=1e-8),p.name
            assert np.allclose(q['episode_months'].sum(0),e[0,0],rtol=1e-12,atol=1e-8),p.name
            assert np.all((months>=MONTH0)&(months<MONTH0+M)),p.name
            assert np.array_equal(a[:,:,C['signals']],sum(a[:,:,C[k]] for k in ['early','late','short','other']))
            assert np.all(e[:,:, :,1]<=e[:,:,:,0]);totals[rec['market']]+=a
            if rec.get('research_source_group')=='inherited':inherited[rec['market']]+=a[2];eps[rec['market']]+=e[2,0]
        checked+=a.size
    old=pd.read_csv(INPUT/'evaluate-metrics.csv');original=pd.read_csv(PRIOR/'docs/uptrend-confirmation-2026-10-23/evaluate-metrics.csv');rows=[]
    for market in ['KR','US']:
        meta=features.metadata(market);ids=[b['id'] for b in meta];v=metrics(inherited[market],eps[market])
        for source,frame,keys in [('extension',old,[b['id'] for b in new_signals.META.values()]),('original',original,[b['id'] for b in meta if b['id'] not in features.NEW])]:
            for key in keys:
                oldrow=frame[(frame.market==market)&(frame.period=='test')&(frame.id==key)].iloc[0]
                for metric in ['known','signals','early','day0','day1_5','late','short','other','before5','precision','capture','mean_delay','first_rise','annual','rate_ratio']:
                    actual=v[metric][ids.index(key)];expected=oldrow[metric]
                    assert np.isclose(actual,expected,rtol=2e-12,atol=1e-8,equal_nan=True),(source,market,key,metric,actual,expected)
                    reconciled+=1
                rows.append(dict(market=market,id=key,source=source,checks=15,status='PASS'))
    pd.DataFrame(allsources).to_csv(OUT/'input-manifest.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(rows).to_csv(OUT/'prior-window-reconciliation.csv',index=False)
    receipt=dict(usable_caches=usable,all_inventory=len(rr),prior_window_values=reconciled,protected_prior_files=len(protected['prior_files'])+3,aggregate_cells_checked=checked,monthly_conservation='PASS',episode_conservation='PASS',partition_conservation='PASS',source_hashes='PASS',finished_utc=datetime.now(timezone.utc).isoformat())
    write(OUT/'verification-final.json',receipt);print(receipt)

if __name__=='__main__':{'preliminary':preliminary,'final':final}[sys.argv[1]]()
