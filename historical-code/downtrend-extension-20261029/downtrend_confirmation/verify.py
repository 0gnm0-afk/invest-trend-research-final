"""Direct correctness checks for research-specific definitions and timing."""
from study import *

def main():
    checks=[]
    # Four positive edges,12 negative edges, then positive: onset is edge4.
    slopes=np.r_[np.full(4,.01),np.full(12,-.01),np.full(5,.01)]
    fit=np.r_[0,np.cumsum(slopes)];seg=np.zeros(len(fit),int);lab=labels(fit,seg)
    assert lab['starts'].tolist()==[4] and lab['ends'].tolist()==[16]
    assert np.flatnonzero(lab['cls']==1).tolist()==list(range(4,10))
    assert lab['cls'][3]==0 and lab['cls'][10]==2
    checks.append('Day0..5 is six dates; before-start is not success; day6 is late')
    short=labels(np.r_[0,np.cumsum(np.r_[np.ones(3),-np.ones(9),np.ones(3)])],np.zeros(16,int))
    assert (short['cls']==3).sum()==9
    cens=labels(np.r_[0,np.cumsum(np.r_[np.ones(3),-np.ones(12)])],np.zeros(16,int))
    assert not cens['known'][3:-1].any()
    checks.append('Nine-day decline is short; terminal unfinished decline is excluded')
    base=np.zeros(12,np.int8);base[2]=1;weak=np.zeros(12);weak[3:9]=1;break20=np.zeros(12);break20[3]=1
    x=extensions(base,weak,break20)
    assert np.flatnonzero(x[:,1]==1).tolist()==[3]
    assert np.flatnonzero(x[:,2]==1).tolist()==[5]
    assert not (x[2]==1).any()
    for t in range(1,13):assert np.array_equal(x[:t],extensions(base[:t],weak[:t],break20[:t]))
    checks.append('Sequence/persistence emit actual confirmation date and pass every-prefix causality')
    n=150;z=dict(close=np.arange(n)+100.,open=np.arange(n)+100.5,high=np.arange(n)+102.,low=np.arange(n)+99.,segment=np.zeros(n,int))
    paths=forward(z)
    assert np.allclose(paths[5][2],[107/103.5-1,102/103.5-1,109/103.5-1])
    z['segment'][5:]=1;assert np.isnan(forward(z)[5][2]).all()
    checks.append('Next open is origin;5-bar path ends t+5; gaps disallow path')
    # Brute-force count precision across all states, not DOWN-conditioned.
    f=np.zeros((len(fit),2),np.int8);f[[3,4,6,10],0]=1;f[4,1]=-1
    paths={h:np.zeros((len(fit),3)) for h in [5,21,63]}
    a=add_stats(f,lab['known'],lab,paths,np.full(len(fit),np.nan),np.zeros(len(fit),bool))
    assert a[0,C['signals']]==4 and a[0,C['early']]==2 and a[0,C['late']]==1 and a[0,C['other']]==1
    checks.append('All-signal denominator includes pre-onset and late events; missing excluded')
    write(OUT/'verification-synthetic.json',dict(status='PASS',checks=checks))
    print('PASS',len(checks),checks)

if __name__=='__main__':main()
