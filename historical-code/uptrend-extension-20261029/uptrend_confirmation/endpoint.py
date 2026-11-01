"""Future-price contamination audit and retrospective label revision experiment."""
from study import *
from l1_solver import l1trend

def compare(a,b,flags,dates,cut,market,symbol,kind):
    n=len(a['cls']);idx=np.arange(n);distance=n-1-idx;rows=[]
    for lo,hi in [(0,20),(21,63),(64,126),(127,252),(253,100000)]:
        region=(distance>=lo)&(distance<=hi)
        if kind=='train_vs_full':region&=(dates>='2016-01-01')&(dates<='2021-12-31')
        known=region&a['known']&b['known'];earlya=a['cls']==1;earlyb=b['cls']==1
        aa=a['starts'][(a['ends']-a['starts']>=10)&region[a['starts']]]
        bb=b['starts'][(b['ends']-b['starts']>=10)&region[b['starts']]]
        # Greedy chronological one-to-one matching; unmatched stays unmatched.
        pairs=[];used=set()
        for x in aa:
            can=[int(y) for y in b['starts'][b['ends']-b['starts']>=10] if abs(int(y)-int(x))<=5 and int(y) not in used]
            if can:
                y=min(can,key=lambda y:(abs(y-int(x)),y));used.add(y);pairs.append((int(x),y))
        sig=flags[known]==1
        rows.append(dict(market=market,symbol=symbol,kind=kind,cutoff=cut,distance_lo=lo,distance_hi=hi,days=int(region.sum()),both_known=int(known.sum()),prefix_unknown=int((region&~a['known']).sum()),long_unknown=int((region&~b['known']).sum()),early_disagree=int((known&(earlya!=earlyb)).sum()),prefix_onsets=len(aa),long_onsets=len(bb),matched5=len(pairs),exact=sum(x==y for x,y in pairs),absolute_shift_sum=sum(abs(x-y) for x,y in pairs),signals=int(sig.sum()),signal_label_disagree=int((sig&(earlya[known]!=earlyb[known])[:,None]).sum()),prefix_signal_hits=int((sig&earlya[known,None]).sum()),long_signal_hits=int((sig&earlyb[known,None]).sum())))
    return rows

def one(rec):
    z=load(rec);rr=[];fits=[]
    if z is None:return [],[],False
    # Select one uninterrupted segment spanning the2024 cutoff and >=600 bars.
    target=np.flatnonzero(z['date']<='2024-12-31')
    if not len(target):return [],[],False
    g=z['segment'][target[-1]];ix=np.flatnonzero(z['segment']==g)
    if (z['date'][ix]<='2024-12-31').sum()<600 or len(ix)<726:return [],[],False
    if z['date'][target[-1]]<'2024-12-01' or z['date'][ix[-1]]<'2025-09-30':return [],[],False
    full=labels(z['full'][ix],np.zeros(len(ix),int))
    for cut in ['2020-12-31','2021-12-31','2023-12-31','2024-12-31']:
        jj=ix[z['date'][ix]<=cut]
        if len(jj)<300:continue
        fitted,info=l1trend(np.log(z['close'][jj]),1.,tol=1e-8);assert info['primal_dual_gap']<1e-8
        a=labels(fitted,np.zeros(len(jj),int))
        # Keep long-fit completed boundaries, including runs continuing beyond
        # the prefix; truncating labels before structure() would censor these.
        b={k:v[:len(jj)] if k not in ['starts','ends'] else v.copy() for k,v in full.items()}
        keep=b['starts']<len(jj);b['starts']=b['starts'][keep];b['ends']=b['ends'][keep]
        rr+=compare(a,b,z['flags'][jj],z['date'][jj],cut,rec['market'],rec['symbol'],'prefix_vs_full')
        fits.append(dict(market=rec['market'],symbol=rec['symbol'],cutoff=cut,actual_last=str(z['date'][jj[-1]]),bars=len(jj),**info))
    # TRAIN labels in cache were fitted ONLY through2022. Comparison does not
    # replace them in selection; it measures what full-sample fitting changes.
    jj=ix[z['date'][ix]<='2022-12-31']
    if len(jj)>=300:
        a=labels(z['train'][jj],np.zeros(len(jj),int));b={k:v[:len(jj)] if k not in ['starts','ends'] else v.copy() for k,v in full.items()};keep=b['starts']<len(jj);b['starts']=b['starts'][keep];b['ends']=b['ends'][keep]
        rr+=compare(a,b,z['flags'][jj],z['date'][jj],'2022-12-31',rec['market'],rec['symbol'],'train_vs_full')
    return rr,fits,True

def main():
    rows=[];fits=[];selected=[]
    for m in ['KR','US']:
        candidates=sorted([r for r in records() if r['market']==m],key=lambda r:hashlib.sha256(r['symbol'].encode()).hexdigest())
        got=0
        for r in candidates:
            rr,ff,ok=one(r)
            if not ok:continue
            rows+=rr;fits+=ff;selected.append(r['symbol']);got+=1
            if got%10==0:print('endpoint',m,got,flush=True)
            if got==40:break
    pd.DataFrame(rows).to_csv(OUT/'endpoint-details.csv',index=False,encoding='utf-8-sig')
    df=pd.DataFrame(rows);df.groupby(['market','kind','distance_lo','distance_hi']).sum(numeric_only=True).reset_index().to_csv(OUT/'endpoint-summary.csv',index=False,encoding='utf-8-sig')
    write(OUT/'endpoint-fits.json',dict(selected=selected,fits=fits,selection='First40 SHA256-ordered eligible symbols per market; no outcome-based selection'))

if __name__=='__main__':main()
