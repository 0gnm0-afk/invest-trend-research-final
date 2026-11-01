"""Crossed stock/time multiplier bootstrap of signal-day sufficient statistics."""
from study import *
from scipy.stats import norm

def main():
    wanted=['signals','early','ordinary_days','ordinary_signals','early_days','match_signals','match_early','match_control_expected']
    jj=[C[k] for k in wanted];B=1000;rng=np.random.default_rng(21021);result=[]
    for m in ['KR','US']:
        files=sorted((OUT/'evaluate').glob(m+'_*.npz'));meta=json.loads((OUT/f'evaluate-{m}-features.json').read_bytes());p=len(meta)
        qs=np.arange(2023*4+1,2025*4+3);arr=np.zeros((len(qs),len(files),p,len(jj)),np.float32)
        for si,path in enumerate(files):
            with np.load(path) as q:
                for quarter,cell in zip(q['quarters'],q['cells']):arr[int(quarter-qs[0]),si]=cell[:,jj]
        sw=rng.poisson(1,(B,len(files))).astype(np.float32);tw=rng.poisson(1,(B,len(qs))).astype(np.float32)
        boot=np.zeros((B,p,len(jj)),np.float64)
        for qi in range(len(qs)):
            val=(sw@arr[qi].reshape(len(files),-1)).reshape(B,p,-1)
            boot+=val*tw[:,qi,None,None]
        point=arr.sum(axis=(0,1),dtype=np.float64)
        def calc(a):
            n,h,od,os,ed,mn,mh,mc=np.moveaxis(a,-1,0)
            er=divide(h,ed);orr=divide(os,od)
            return dict(precision=divide(h,n),early_rate=er,ordinary_rate=orr,rate_difference=er-orr,rate_ratio=divide(er,orr),context_difference=divide(mh-mc,mn))
        bvals=calc(boot);pts=calc(point);family=2*sum(len(json.loads((OUT/f'evaluate-{mm}-features.json').read_bytes())) for mm in ['KR','US'])
        zcrit=norm.ppf(1-.05/(2*family))
        for j,b in enumerate(meta):
            row=dict(market=m,id=b['id'],bootstrap_replicates=B,quarter_clusters=len(qs),stock_clusters=len(files),family_tests=family)
            for k in pts:
                vals=bvals[k][:,j];pointval=float(pts[k][j]);se=float(np.nanstd(vals,ddof=1));lo,hi=np.nanquantile(vals,[.025,.975])
                row.update({k+'_low':lo,k+'_high':hi,k+'_se':se})
                if k in ['rate_difference','context_difference']:
                    row.update({k+'_adjusted_low':pointval-zcrit*se,k+'_adjusted_high':pointval+zcrit*se,k+'_adjusted_p':min(1,2*norm.sf(abs(pointval)/se)*family) if se else None})
            result.append(row)
        print('bootstrap',m,len(files),'stocks',len(qs),'quarters',flush=True)
    pd.DataFrame(result).to_csv(OUT/'uncertainty.csv',index=False,encoding='utf-8-sig')
    df=pd.read_csv(OUT/'evaluate-metrics.csv');u=pd.DataFrame(result);test=df[df.period=='test'].merge(u,on=['market','id'],validate='one_to_one');test.to_csv(OUT/'test-results.csv',index=False,encoding='utf-8-sig')

if __name__=='__main__':main()
