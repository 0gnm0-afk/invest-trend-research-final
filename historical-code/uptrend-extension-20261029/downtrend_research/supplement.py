"""Include unique histories outside the pinned current-listing archive, no duplicates."""
from run import ROOT,OUT,write,sha,summarize_one,save_arrays
from pathlib import Path
import json,sqlite3,hashlib
import numpy as np
from features import calculate
from l1_solver import l1trend
from market_scope import load,match

PRIOR=Path('<USER_HOME>/Documents/Codex/2026-10-18/referenced-chatgpt-conversation-this-is-an')

def fit_save(rec,z):
    ds=z['date'];keep=ds<='2026-09-30';z={k:v[keep] for k,v in z.items()};ds=z['date'];n=len(ds)
    full=np.full(n,np.nan);train=full.copy();atr=full.copy();context=np.zeros((n,3),np.int8);f=None;a=dict(rec,stored_bars=n,used_bars=n,source_first=str(ds[0]),source_last=str(ds[-1]),segments=int(len(np.unique(z['segment']))),fits=[],status='ok',invalid_or_zero_volume=0)
    for sg in np.unique(z['segment']):
        ix=np.flatnonzero(z['segment']==sg)
        if len(ix)<80:continue
        ff,names,ctx,at=calculate({k:z[k][ix] for k in ['open','high','low','close','volume']})
        if f is None:f=np.full((n,len(names)),-1,np.int8)
        f[ix]=ff;context[ix]=ctx;atr[ix]=at
        for mode,target,cut in [('train',train,'2022-12-31'),('full',full,'2026-09-30')]:
            jj=ix[ds[ix]<=cut]
            if len(jj)<80:continue
            target[jj],info=l1trend(np.log(z['close'][jj]),1,tol=1e-8);a['fits'].append(dict(mode=mode,segment=int(sg),n=len(jj),**info))
    path=OUT/'cache'/f"{rec['market']}_{rec['symbol']}.npz"
    if f is None:
        a['status']='no_long_segment';write(path.with_suffix('.json'),a);return
    save_arrays(path,**z,full=full,train=train,flags=f,context=context,atr=atr)
    a['cache_sha256']=sha(path);write(path.with_suffix('.json'),a)

def main():
    inv=json.loads((OUT/'inventory.json').read_bytes());known={(r['market'],r['symbol'].split('.')[0] if r['market']=='KR' else r['symbol']) for r in inv['stocks']+inv['excluded']}
    policy=load();added=[];excluded=[]
    prior=json.loads((PRIOR/'work/ma-work-data/dataset.json').read_bytes())['stocks']
    vroot=PRIOR/'outputs/ma-downside-factors-20261019/volume_arrays'
    vhash={r['path']:r['sha256'] for r in json.loads((vroot.parent/'manifest.json').read_bytes())}
    for r in prior:
        if (r['market'],r['symbol']) in known:continue
        assert r['market']=='KR'
        symbol=r['symbol']+'.KS';exc=match(dict(market='KR',symbol=symbol),policy,completed_session='2026-09-30')
        if exc and exc['reason']!='confirmed_trading_ended':excluded.append(dict(market='KR',symbol=symbol,reason=exc['reason']));continue
        source=PRIOR/'work/ma-work-data'/r['path'];assert sha(source)==r['sha256']
        vp=vroot/f"KR_{r['symbol']}.npz";assert sha(vp)==vhash['volume_arrays/'+vp.name]
        with np.load(source,allow_pickle=False) as q:z={k:q[k] for k in ['date','segment','open','high','low','close']}
        with np.load(vp,allow_pickle=False) as q:
            assert np.array_equal(q['date'],z['date']);z['volume']=q['volume']
            # The previous audited volume extractor flags split/share jumps.
            # Its NaN volume windows stay unavailable for volume indicators.
            jump=q['split_or_share_jump']
            for t in np.flatnonzero(jump):z['volume'][t:min(len(jump),t+21)]=np.nan
        rec=dict(market='KR',symbol=symbol,exchange='KOSPI (prior dataset)',isin=None,source=str(source),source_sha256=sha(source),volume_source=str(vp),volume_sha256=sha(vp),source_kind='prior_unique_history',note='Historical-only inclusion; not restored to operating collection')
        fit_save(rec,z);added.append(rec)
    db=ROOT/'runtime/chart-history.sqlite3';con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
    rows=con.execute('select identity,payload,sha256 from history').fetchall();best={}
    for identity,payload,h in rows:
        assert hashlib.sha256(payload.encode()).hexdigest()==h
        q=json.loads(payload);s=q.get('series',{});key=s.get('market'),s.get('symbol')
        normalized=(key[0],key[1].split('.')[0] if key[0]=='KR' else key[1])
        if key[0] is None or normalized in known or q.get('history',{}).get('state')!='complete':continue
        if key not in best or len(s['bars'])>len(best[key][1]['series']['bars']):best[key]=(identity,q,h)
    (OUT/'supplement_inputs').mkdir(exist_ok=True)
    for (m,s),(identity,q,h) in best.items():
        exc=match(dict(market=m,symbol=s),policy,completed_session='2026-09-30')
        if exc:excluded.append(dict(market=m,symbol=s,reason=exc['reason']));continue
        source=OUT/'supplement_inputs'/f'{m}_{s}.json';write(source,q)
        bars=[b for b in q['series']['bars'] if b['date']<='2026-09-30'];ds=np.array([b['date'] for b in bars],dtype='U10')
        assert np.array_equal(ds,np.unique(ds));z={k:np.array([b[k] for b in bars],float) for k in ['open','high','low','close','volume']}
        assert np.all(z['low']>0)&np.all(z['high']>=np.maximum(z['open'],z['close']))&np.all(z['low']<=np.minimum(z['open'],z['close']))
        # Explicit calendar continuity for these three US ADR histories.
        import exchange_calendars as xc
        cal=xc.get_calendar('XNYS',start=str(ds[0]),end=str(ds[-1]));sessions=cal.sessions.strftime('%Y-%m-%d').to_numpy();pos=np.searchsorted(sessions,ds)
        calendar_valid=np.isin(ds,sessions)
        valid=(z['volume']>0)&calendar_valid;oldix=np.flatnonzero(valid);ds=ds[valid];pos=pos[valid];z={k:v[valid] for k,v in z.items()}
        seg=np.cumsum(np.r_[True,(np.diff(pos)!=1)|(np.diff(oldix)!=1)])-1;z.update(date=ds,segment=seg)
        rec=dict(market=m,symbol=s,exchange='saved chart ADR',isin=None,source=str(source),source_sha256=sha(source),source_kind='selected_chart_history',db_reference=str(db),row_identity=identity,row_sha256=h,price_basis=q['series'].get('price_basis'),excluded_calendar_bars=int((~calendar_valid).sum()),excluded_zero_volume=int((~valid&calendar_valid).sum()))
        fit_save(rec,z);added.append(rec)
    # Append only new identities; rerunning never duplicates the universe.
    old={(r['market'],r['symbol']) for r in inv['stocks']}
    inv['stocks'] += [r for r in added if (r['market'],r['symbol']) not in old]
    inv['supplemental_excluded']=excluded;write(OUT/'inventory.json',inv)
    write(OUT/'supplemental_sources.json',dict(added=[r for r in inv['stocks'] if r.get('source_kind')],excluded=excluded))
    for r in added:summarize_one(r)
    print('supplemental stocks',len(added),'excluded',excluded,flush=True)

if __name__=='__main__':main()
