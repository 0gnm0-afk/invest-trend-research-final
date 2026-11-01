"""Ledger reconciliation, independent path/match checks and review artifacts."""
from study import *
from paths import focal,population,outcomes,HORIZONS,OUTCOMES,Q,K,WIDTH
import gzip,csv,shutil

DOC=ROOT/'docs/research/downtrend-extension-2026-10-29'

def finish():
    DOC.mkdir(exist_ok=True);rows=[];cases=[];checks=[];inputs=[];ledger_n=0;scalar_n=0;match_n=0;label_n=0;benchmark_cells=0;prior=json.loads((OUT/'protocol-receipt.json').read_bytes())
    for rel,h in prior['prior_files'].items():assert sha(ROOT/rel)==h,rel
    assert sha(OLD/'inventory.json')==prior['inventory_sha256']
    stats=pd.read_csv(OUT/'evaluate-metrics.csv');stats=stats[stats.period=='test'].set_index(['market','id'])
    records_by={(r['market'],r['symbol']):r for r in records()}
    # Every output checks the immutable original source cache SHA when loaded.
    with gzip.open(OUT/'all-signal-ledger.csv.gz','wt',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['market','symbol','id','date','early_hit','label_class','age','duration','onset_date','already_drop']+[f'{o}_{h}' for h in HORIZONS for o in OUTCOMES])
        for m in ['KR','US']:
            ids=focal(m);bags=[[] for _ in ids];locs=[[] for _ in ids];totals=np.zeros((len(ids),1+Q));global_i=0;population_missing=np.zeros(len(ids),int)
            for file in sorted((OUT/'paths').glob(m+'_*.npz')):
                symbol=file.stem.split('_',1)[1];rec=records_by[m,symbol]
                with np.load(file) as q:a=q['ledger'];cells=q['cells'];sup=q['support']
                totals+=cells[:,:,:1+Q].sum(0,dtype=np.float64)
                assert np.allclose(cells[:,:,0].sum(0),sup[0,:,0])
                for sc in range(4):assert np.allclose(cells[:,:,1+Q+sc*WIDTH].sum(0),sup[sc,:,1])
                # Dates only are cheap to load; all source hashes checked below.
                src=OLD/'cache'/file.name;source_cache_hash=sha(src);assert source_cache_hash==json.loads(src.with_suffix('.json').read_bytes())['cache_sha256']
                new=OUT/'features'/file.name;newmeta=json.loads(new.with_suffix('.json').read_bytes())
                assert sha(new)==newmeta['cache_sha256'] and sha(Path(signals.__file__))==newmeta['code_sha256'] and newmeta['source_sha256']==source_cache_hash
                inputs.append(dict(market=m,symbol=symbol,source=rec['source'],source_sha256=rec['source_sha256'],original_cache=str(src.relative_to(ROOT)),original_cache_sha256=newmeta['source_sha256'],new_features_sha256=newmeta['cache_sha256']))
                with np.load(src) as zz,np.load(new) as nf:
                    dates=zz['date']
                    original_ids=list(signals.original.META);new_ids=[b['id'] for b in BASE]
                    for key in signals.BENCHMARKS:
                        left=nf['flags'][:,new_ids.index(key)];right=zz['flags'][:,original_ids.index(key)]
                        assert np.array_equal(left,right),(m,symbol,key,'old benchmark changed')
                        benchmark_cells+=len(left)
                    assert np.array_equal(nf['context'],zz['context'])
                    assert np.allclose(nf['atr'],zz['atr'],equal_nan=True)
                with np.load(OUT/'evaluate'/file.name) as ev:
                    meta0=json.loads((OUT/f'evaluate-{m}-features.json').read_bytes());expected_hits=ev['totals'][1,[[b['id'] for b in meta0].index(k) for k in ids],C['early']]
                ledger_hits=np.array([a[a[:,0]==j,2].sum() for j in range(len(ids))])
                if not np.array_equal(expected_hits,ledger_hits):
                    zz=load(rec);ff,meta0=feature_set(zz,m,True);ll=labels(zz['full'],zz['segment']);rr,_,_,_,_=population(zz)
                    nn=len(rr);hist=np.zeros(nn,bool);fut=np.zeros(nn,bool);hist[65:]=zz['segment'][65:]==zz['segment'][:-65]
                    if nn>126:fut[:-126]=(zz['segment'][:-126]==zz['segment'][126:])&np.isfinite(zz['full'][126:])
                    success=(zz['date']>='2023-04-01')&(zz['date']<='2025-09-30')&hist&fut&(ll['cls']==1)
                    for j,key in enumerate(ids):
                        missing=np.flatnonzero(success&(ff[:,[b['id'] for b in meta0].index(key)]==1)&~rr)
                        assert expected_hits[j]-ledger_hits[j]==len(missing),(m,symbol,key)
                        assert np.all(~np.isfinite(zz['covariates'][missing]).all(1)),(m,symbol,key,'unexpected population difference')
                        population_missing[j]+=len(missing)
                for j,key in enumerate(ids):
                    sub=a[a[:,0]==j];bags[j].append(sub)
                    locs[j].extend([(symbol,int(t)) for t in sub[:,1]])
                    for r in sub:
                        t=int(r[1]);orig=int(r[6]);writer.writerow([m,symbol,key,dates[t],int(r[2]),int(r[3]),int(r[4]),int(r[5]),dates[orig] if orig>=0 else '',r[7],*r[8:]])
                ledger_n+=len(a);global_i+=1
                auditfile=file.with_suffix('.json')
                # Deterministic price samples, not selected by success or return.
                do_sample=int(hashlib.sha256((m+symbol).encode()).hexdigest()[:8],16)%101==0
                if do_sample or auditfile.exists():
                    z=load(rec);ff,meta=feature_set(z,m,True);lab=labels(z['full'],z['segment']);risk,pp,mo,qu,strata=population(z)
                    if do_sample:
                        for r in a[::max(1,len(a)//8)][:8]:
                            j,t=int(r[0]),int(r[1]);assert ff[t,[b['id'] for b in meta].index(ids[j])]==1 and risk[t]
                            direct=[]
                            for h in HORIZONS:
                                op=z['open'][t+1];hi=max(z['high'][t+1:t+h+1])/op-1;lo=min(z['low'][t+1:t+h+1])/op-1;ret=z['close'][t+h]/op-1
                                direct.extend([hi>=.05,hi>=.1,lo<=-.05,lo<=-.1,max(0,hi),max(0,-lo),ret,ret>0]);scalar_n+=1
                            assert np.allclose(r[8:],direct)
                            expected=any(s<=t<=s+5 for s,e in zip(lab['starts'],lab['ends']) if e-s>=10)
                            eligible126=t+126<len(z['date']) and z['segment'][t]==z['segment'][t+126] and np.isfinite(z['full'][t+126])
                            assert bool(r[2])==bool(expected and eligible126);label_n+=1
                        # Independent slope/run classifier over full sample.
                        sl=np.r_[np.diff(z['full']),np.nan];sl[np.r_[np.diff(z['segment'])!=0,True]]=np.nan
                        up=sl<-1e-6;start=None;starts=[];ends=[]
                        for t in range(len(sl)):
                            if up[t] and (t==0 or not up[t-1]):start=t
                            if start is not None and not up[t]:
                                if start>0 and np.isfinite(sl[start-1]) and np.isfinite(sl[t]):starts.append(start);ends.append(t)
                                start=None
                        assert starts==lab['starts'].tolist() and ends==lab['ends'].tolist()
                    if auditfile.exists():
                        for audit in json.loads(auditfile.read_bytes()):
                            j=[b['id'] for b in meta].index(audit['id']);t=audit['signal'];nn=np.array(audit['controls'],int);ix=np.r_[t,nn]
                            assert ff[t,j]==1 and np.all(ff[nn,j]==0) and risk[ix].all()
                            assert len(set(qu[ix]))==1 and len(set(strata[audit['scheme']][ix]))==1
                            yy=[]
                            for tt in ix:
                                row=[]
                                for h in HORIZONS:
                                    op=z['open'][tt+1];hi=max(z['high'][tt+1:tt+h+1])/op-1;lo=min(z['low'][tt+1:tt+h+1])/op-1;ret=z['close'][tt+h]/op-1
                                    row.extend([hi>=.05,hi>=.1,lo<=-.05,lo<=-.1,max(0,hi),max(0,-lo),ret,ret>0]);match_n+=1
                                yy.append(row)
                            assert np.allclose(yy[0],audit['signal_outcomes']) and np.allclose(np.mean(yy[1:],0),audit['control_mean'])
                if global_i%500==0:print('audit',m,global_i,flush=True)
            for j,key in enumerate(ids):
                a=np.concatenate(bags[j]);assert np.isclose(len(a),totals[j,0]);assert np.allclose(a[:,8:].sum(0),totals[j,1:],rtol=2e-5,atol=.02)
                # Classifier success count must agree despite the larger path population.
                expected=stats.loc[(m,key),'early'];assert int(a[:,2].sum())+population_missing[j]==int(expected),(m,key,a[:,2].sum(),expected)
                checks.append(dict(market=m,id=key,path_signals=len(a),classifier_hits=int(expected),path_early_hits=int(a[:,2].sum()),early_hits_excluded_missing_observable_covariates=int(population_missing[j]),ledger='PASS'))
                for pop,mask in [('all',np.ones(len(a),bool)),('early_hit',a[:,2]==1)]:
                    for hi,h in enumerate(HORIZONS):
                        for oi,outcome in enumerate(OUTCOMES):
                            v=a[mask,8+hi*8+oi]
                            rows.append(dict(market=m,id=key,population=pop,horizon=h,outcome=outcome,n=len(v),mean=np.mean(v),q10=np.quantile(v,.1),median=np.median(v),q90=np.quantile(v,.9),minimum=np.min(v),maximum=np.max(v)))
                hit=a[a[:,2]==1,7];rows.append(dict(market=m,id=key,population='early_hit',horizon=0,outcome='already_drop',n=len(hit),mean=np.mean(hit),q10=np.quantile(hit,.1),median=np.median(hit),q90=np.quantile(hit,.9),minimum=np.min(hit),maximum=np.max(hit)))
                # Actual examples: median-return early success and non-early failure.
                # Selection intentionally illustrates the group; not independent evidence.
                if key in list(dict.fromkeys([json.loads((OUT/'frozen.json').read_bytes())[m][0],'macd_rsi60'])):
                    for kind,mask in [('early_success',a[:,2]==1),('not_early',a[:,3]==0),('late',a[:,3]==2)]:
                        ix=np.flatnonzero(mask)
                        if not len(ix):continue
                        target=np.median(a[ix,8+8+6]);order=ix[np.argsort(abs(a[ix,8+8+6]-target),kind='stable')]
                        for jj in order[:100]:
                            sym,t=locs[j][jj];z=load(records_by[m,sym])
                            if t>=30 and t+63<len(z['date']) and z['segment'][t-30]==z['segment'][t+63]:break
                        else:continue
                        r=a[jj];cases.append(dict(market=m,id=key,kind=kind,symbol=sym,index=t,date=str(z['date'][t]),onset_date=str(z['date'][int(r[6])]) if r[6]>=0 else '',age=int(r[4]),duration=int(r[5]),next_open=float(z['open'][t+1]),onset_close=float(z['close'][int(r[6])]) if r[6]>=0 else None,already_drop=float(r[7]),return21=float(r[22]),favorable21=float(r[20]),adverse21=float(r[21]),selection='nearest group median21 terminal return, continuous30 prior/63 future; illustrative'))
    # Every classifier summary obeys disjoint outcome and episode identities.
    raw=pd.read_csv(OUT/'evaluate-metrics.csv')
    assert np.allclose(raw.signals,raw.day0+raw.day1_5+raw.late+raw.short+raw.other)
    assert (raw.captured<=raw.episodes).all() and (raw.signals<=raw.known).all()
    assert np.allclose(raw.precision,raw.early/raw.signals,equal_nan=True)
    train=raw[raw.period=='train'].set_index(['market','id']);sel=pd.read_csv(OUT/'select-metrics.csv').set_index(['market','id'])
    for key,r in sel.iterrows():
        for k in ['signals','early','known','captured','episodes']:assert np.isclose(r[k],train.loc[key,k]),(key,k)
    for name in ['base-rates','matched-paths']:
        a=pd.read_csv(OUT/f'{name}.csv');assert np.isfinite(a.select_dtypes('number')).all().all()
        if name=='base-rates':assert np.allclose(a.precision-a.base_rate,a.difference)
        else:
            assert np.allclose(a.signal-a.control,a.difference);assert (a.matched_signals<=a.all_signals+.1).all()
            assert (a.sim_low<=a.difference).all() and (a.sim_high>=a.difference).all()
    pd.DataFrame(rows).to_csv(OUT/'path-distributions.csv',index=False);pd.DataFrame(cases).to_csv(OUT/'illustrated-cases.csv',index=False);pd.DataFrame(inputs).to_csv(OUT/'input-manifest.csv',index=False)
    for m in ['KR','US']:
        meta=json.loads((OUT/f'evaluate-{m}-features.json').read_bytes());pd.DataFrame(meta).assign(market=m).to_csv(DOC/f'{m}-signal-definitions.csv',index=False)
    for file in OUT.glob('*.csv'):shutil.copyfile(file,DOC/file.name)
    for name in ['frozen.json','selection-receipt.json','verification-synthetic.json','classification-inference.json','paths-inference.json','paths-compute-receipt.json']:
        shutil.copyfile(OUT/name,DOC/name)
    result=dict(status='PASS',original_files_unchanged=len(prior['prior_files']),inventory_sha256=prior['inventory_sha256'],original_benchmark_flag_cells=benchmark_cells,ledger_rows=ledger_n,scalar_horizon_checks=scalar_n,matched_horizon_checks=match_n,independent_label_checks=label_n,ledger_reconciliations=checks,classification_rows=len(raw),selection_training_totals_unchanged=True)
    write(DOC/'reproduction-manifest.json',dict(code={str(p.relative_to(ROOT)):sha(p) for p in Path(__file__).parent.glob('*.py')},csv={p.name:sha(p) for p in DOC.glob('*.csv')},input_caches=len(inputs),source_raw_hashes_inherited_not_newly_reaudited=True))
    write(OUT/'verification-final.json',result);write(DOC/'verification-final.json',result);print(result,flush=True)

if __name__=='__main__':finish()
