"""Bounded-memory descriptive distribution supplement, without new hypotheses.

Added after pooled aggregation highlighted a large mean first-confirmation rise
for rare US TRIX-zero successes. No event, label, eligibility or matching rule
changes. Values are spooled as float32; exact empirical linear quantiles refer
to those stored values. Means/counts reconcile against pre-existing statistics.
"""
from paths import *
from cases import price_source
import heapq

DOC = ROOT / 'docs/research/uptrend-longhistory-2026-10-29'
SPOOL = OUT / 'distributions' / 'spool-v1'
QUANTILES = [('q05', .05), ('q10', .10), ('q25', .25), ('median', .5),
             ('q75', .75), ('q90', .9), ('q95', .95)]
CONTINUOUS = ['return', 'favorable', 'adverse']


def path_file(market, key, population):
    return SPOOL / f'{market}_{key}_{population}.f32'


def first_file(market, key):
    return SPOOL / f'{market}_{key}_first.f32'


def build(rebuild=False):
    receipt = OUT / 'distributions' / 'spool-complete.json'
    if receipt.exists() and not rebuild:
        assert SPOOL.is_dir(), 'Temporary spool was cleaned; regenerate with --rebuild-spool'
        return json.loads(receipt.read_bytes())
    expected = {f"{r['market']}_{r['symbol']}" for r in records()
                if Path(r.get('cache_path', r.get('research_cache', str(OLD/'cache'/f"{r['market']}_{r['symbol']}.npz")))).exists()}
    actual = {p.stem for p in (OUT / 'paths').glob('*.npz')}
    assert actual == expected and len(actual) == 7293, (len(expected),len(actual),len(expected-actual))
    assert not SPOOL.exists(), 'Incomplete existing spool: preserve/audit it before a new run'
    SPOOL.mkdir(parents=True)
    handles = {}; stats = {}; firststats = {}; extremes = {}
    def append(path, values):
        if path not in handles:
            handles[path] = path.open('wb')
        values.astype(np.float32).tofile(handles[path])
    for m in ['KR','US']:
        for key in focal(m):
            for pop in ['all_signals','early_confirmation_success']:
                stats[(m,key,pop)] = dict(n=0, total=np.zeros(9), positive=np.zeros(3), reference=np.zeros(9), reference_positive=np.zeros(3))
            firststats[(m,key)] = dict(n=0,total=0.,expected_n=0,expected_total=0.)
            extremes[(m,key)] = []
    processed = 0; start = time.monotonic(); max_first_sum_error = 0.; max_path_sum_error = 0.
    try:
        for rec in sorted(records(),key=lambda r:(r['market'],r['symbol'])):
            m=rec['market']; stem=f"{m}_{rec['symbol']}"; file=OUT/'paths'/(stem+'.npz')
            if not file.exists():continue
            with np.load(file,allow_pickle=False) as q:
                ledger=q['ledger_index']; ids=q['ids'].tolist(); allids=q['all_ids'].tolist()
                raw=q['raw'].sum(0,dtype=np.float64); hitraw=q['hit'].sum(0,dtype=np.float64)
            z=price_source(rec); pa=forward(z)
            feature_file=OUT/'features'/(stem+'.npz')
            if feature_file.exists():
                with np.load(feature_file,allow_pickle=False) as q: flags=q['flags']
            else:
                # Optional replay after this task's regenerable feature cache
                # was cleaned. Immutable source prices/fits remain the input.
                (OUT/'features').mkdir(parents=True,exist_ok=True)
                flags=load(rec)['flags']
            with np.load(OUT/'evaluate'/(stem+'.npz'),allow_pickle=False) as q: expected_ep=q['episodes'][0,0]
            ff=flags[:,[allids.index(key) for key in ids]]; n=len(z['date']); seg=z['segment']
            lab=labels(z['full'],seg)
            hist=np.zeros(n,bool); future=np.zeros(n,bool)
            if n>65:hist[65:]=seg[65:]==seg[:-65]
            if n>126:future[:-126]=(seg[:-126]==seg[126:])&np.isfinite(z['full'][126:])
            valid=(z['date']>=START)&(z['date']<=END)&hist&future&np.isfinite(lab['slope'])&lab['known']
            first=[[] for _ in ids]
            for t,b in zip(lab['starts'],lab['ends']):
                if b-t<10 or not valid[t:t+6].all():continue
                f=ff[t:t+6]; captured=(f>=0).all(0)&(f==1).any(0)
                for j in np.flatnonzero(captured):
                    delay=int(np.argmax(f[:,j]==1)); ts=t+delay
                    value=float(z['open'][ts+1]/z['close'][t]-1); first[j].append(value)
                    entry=(value,rec['symbol'],str(z['date'][t]),str(z['date'][ts]),
                           float(z['close'][t]),float(z['open'][ts+1]),int(b-t),delay)
                    heap=extremes[(m,ids[j])]
                    if len(heap)<3:heapq.heappush(heap,entry)
                    elif entry>heap[0]:heapq.heapreplace(heap,entry)
            for j,key in enumerate(ids):
                ai=allids.index(key); ee=expected_ep[ai]; values=np.asarray(first[j],float)
                assert len(values)==int(ee[1])==int(ee[9]),(stem,key,len(values),ee[1])
                error=abs(values.sum()-ee[8]); max_first_sum_error=max(max_first_sum_error,float(error))
                assert np.isclose(values.sum(),ee[8],rtol=1e-10,atol=1e-8),(stem,key,error)
                append(first_file(m,key),values)
                st=firststats[(m,key)];st['n']+=len(values);st['total']+=values.sum();st['expected_n']+=int(ee[1]);st['expected_total']+=ee[8]
                for pop,selected,ref in [('all_signals',ledger[:,0]==j,raw),
                                         ('early_confirmation_success',(ledger[:,0]==j)&(ledger[:,2]==1),hitraw)]:
                    ts=ledger[selected,1]
                    vv=np.column_stack([v for h in HORIZONS for v in [pa[h][ts,0],np.maximum(0,pa[h][ts,2]),np.maximum(0,-pa[h][ts,1])]])
                    assert np.isfinite(vv).all() and len(ts)==int(ref[ai,0]),(stem,key,pop)
                    reference=np.array([ref[ai,1+hi*8+oi] for hi in range(3) for oi in [6,4,5]])
                    error=float(np.max(abs(vv.sum(0)-reference)))
                    max_path_sum_error=max(max_path_sum_error,error)
                    assert np.allclose(vv.sum(0),reference,rtol=2e-6,atol=1e-5),(stem,key,pop,error)
                    append(path_file(m,key,pop),vv)
                    st=stats[(m,key,pop)];st['n']+=len(ts);st['total']+=vv.sum(0);st['reference']+=reference
                    st['positive']+=(vv[:,[0,3,6]]>0).sum(0)
                    st['reference_positive']+=ref[ai,[1+hi*8+7 for hi in range(3)]]
            processed+=1
            if processed%300==0 or processed==len(expected):
                print('distribution spool',processed,'/',len(expected),'seconds',round(time.monotonic()-start),flush=True)
    finally:
        for handle in handles.values():handle.close()
    assert processed==7293
    packed=[]
    for (m,key,pop),st in stats.items():
        assert np.array_equal(st['positive'],st['reference_positive'])
        packed.append(dict(market=m,id=key,population=pop,**{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in st.items()}))
    firstpacked=[dict(market=m,id=key,**st) for (m,key),st in firststats.items()]
    exrows=[]
    for (m,key),heap in extremes.items():
        for rank,item in enumerate(sorted(heap,reverse=True),1):
            value,symbol,onset,signal,close,op,duration,delay=item
            exrows.append(dict(market=m,id=key,rank=rank,symbol=symbol,onset_date=onset,signal_date=signal,
                              onset_close=close,next_open=op,rise=value,duration=duration,delay=delay,
                              interpretation='Largest observed first-confirmation timing rise; diagnostic, not a trade return'))
    pd.DataFrame(exrows).to_csv(OUT/'first-confirmation-extremes.csv',index=False,encoding='utf-8-sig')
    result=dict(stocks=processed,paths=packed,first=firstpacked,max_first_sum_error=max_first_sum_error,
                max_path_sum_error_vs_float32_sufficient_stats=max_path_sum_error,
                bytes=sum(p.stat().st_size for p in SPOOL.glob('*.f32')),
                code_sha256=sha(Path(__file__)),completed_utc=datetime.now(timezone.utc).isoformat())
    write(receipt,result);return result


def describe(path,n,width,column):
    if not n:return {k:np.nan for k in ['mean','min','max','positive_probability']+[q[0] for q in QUANTILES]}
    a=np.memmap(path,dtype=np.float32,mode='r',shape=(n,width))
    # One strided column is copied by quantile: bounded by the largest condition,
    # never a dense all-market/condition array. No winsorization or approximation.
    col=a[:,column];qq=np.quantile(col,[q[1] for q in QUANTILES],method='linear')
    result=dict(mean=float(np.mean(col,dtype=np.float64)),min=float(np.min(col)),max=float(np.max(col)),
                positive_probability=float(np.count_nonzero(col>0)/n))
    result.update({key:float(value) for (key,_),value in zip(QUANTILES,qq)})
    del col,a
    return result


def summarize(receipt):
    rows=[];firstrows=[];max_mean_error=0.
    for st in receipt['paths']:
        m,key,pop,n=st['market'],st['id'],st['population'],st['n']
        path=path_file(m,key,pop);assert path.stat().st_size==n*9*4
        for hi,h in enumerate(HORIZONS):
            for oi,outcome in enumerate(CONTINUOUS):
                j=hi*3+oi;dd=describe(path,n,9,j)
                ref=st['total'][j]/n if n else np.nan
                if n:
                    max_mean_error=max(max_mean_error,abs(dd['mean']-ref))
                    assert np.isclose(dd['mean'],ref,rtol=2e-6,atol=1e-7),(m,key,pop,h,outcome)
                    if outcome=='return':assert np.isclose(dd['positive_probability'],st['positive'][hi]/n,rtol=0,atol=1e-12)
                rows.append(dict(market=m,id=key,population=pop,horizon=h,outcome=outcome,n=n,
                                 reference_mean_float64=ref,**dd,inference='Descriptive empirical quantiles; float32 spool, linear interpolation'))
    primary=pd.read_csv(OUT/'evaluate-metrics.csv').query("period == 'primary'").set_index(['market','id'])
    for st in receipt['first']:
        m,key,n=st['market'],st['id'],st['n'];path=first_file(m,key)
        assert path.stat().st_size==n*4
        dd=describe(path,n,1,0);r=primary.loc[(m,key)]
        assert n==int(r.captured)==st['expected_n']
        if n:assert np.isclose(dd['mean'],r.first_rise,rtol=2e-6,atol=1e-7),(m,key,dd['mean'],r.first_rise)
        firstrows.append(dict(market=m,id=key,captured_episodes=n,eligible_episodes=int(r.episodes),
                              reference_mean_float64=st['total']/n if n else np.nan,**dd,
                              price_basis='First captured signal next open / retrospective onset close - 1',
                              inference='Descriptive; one first alert per fully observable early0..5 episode'))
    DOC.mkdir(parents=True,exist_ok=True)
    for filename,values in [('path-distributions.csv',rows),('first-confirmation-distributions.csv',firstrows)]:
        df=pd.DataFrame(values)
        df.to_csv(OUT/filename,index=False,encoding='utf-8-sig');df.to_csv(DOC/filename,index=False,encoding='utf-8-sig')
    import shutil
    shutil.copy2(OUT/'first-confirmation-extremes.csv',DOC/'first-confirmation-extremes.csv')
    verification=dict(status='PASS',stocks=receipt['stocks'],path_distribution_rows=len(rows),first_distribution_rows=len(firstrows),
        expected_path_rows=51*2*3*3,expected_first_rows=51,
        counts_reconciled='All per-stock raw/hit path counts and first-captured episode counts, then primary aggregates',
        positive_probability_reconciled='Every terminal horizon and population against pre-existing sufficient statistics',
        max_float32_spool_mean_error=max_mean_error,max_first_sum_error=receipt['max_first_sum_error'],
        max_path_sum_error_vs_float32_sufficient_stats=receipt['max_path_sum_error_vs_float32_sufficient_stats'],
        quantiles=[q[0] for q in QUANTILES],method='Exact empirical numpy linear quantile on stored float32 values',
        interpretation='Post-aggregation descriptive supplement; no changed hypotheses, thresholds, populations or trimming',
        disk_spool_bytes=receipt['bytes'],code_sha256=sha(Path(__file__)))
    assert len(rows)==918 and len(firstrows)==51
    write(OUT/'verification-distributions.json',verification);write(DOC/'verification-distributions.json',verification)
    print(json.dumps(verification,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--summarize-only',action='store_true')
    ap.add_argument('--rebuild-spool',action='store_true');args=ap.parse_args()
    assert not (args.summarize_only and args.rebuild_spool)
    result=json.loads((OUT/'distributions/spool-complete.json').read_bytes()) if args.summarize_only else build(args.rebuild_spool)
    summarize(result)
