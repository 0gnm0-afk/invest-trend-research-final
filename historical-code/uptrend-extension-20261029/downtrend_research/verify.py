"""Independent synthetic checks for the research, not operational trading tests."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'runtime/downtrend-indicators-20261021/dependencies'))
import numpy as np
from features import calculate,cross,wilder
from l1_solver import l1trend,pentasolve,fast_pentasolve,d2
from run import structure,window,OUT,write

def main():
    rng=np.random.default_rng(7021);checks=[]
    for n in [8,31,200]:
        diagonal=6+rng.uniform(1,10,n);rhs=rng.normal(size=n)
        A=np.diag(diagonal)+np.diag(np.full(n-1,-4),1)+np.diag(np.full(n-1,-4),-1)+np.diag(np.ones(n-2),2)+np.diag(np.ones(n-2),-2)
        assert np.allclose(fast_pentasolve(diagonal,rhs),np.linalg.solve(A,rhs),atol=1e-11)
        assert np.allclose(pentasolve(diagonal,rhs),fast_pentasolve(diagonal,rhs),atol=1e-11)
    checks.append('banded solver equals dense and prior scalar solver: 3 sizes')
    for kind in ['linear','turn','noise']:
        y=np.arange(100)*.002 if kind=='linear' else np.r_[np.arange(50)*.003,.15-np.arange(50)*.004] if kind=='turn' else np.cumsum(rng.normal(0,.01,100))
        a,aa=l1trend(y,1,tol=1e-8);b,bb=l1trend(y,1,tol=1e-8,scalar=True)
        assert np.max(abs(a-b))<1e-7 and aa['primal_dual_gap']<1e-8
        assert abs(aa['objective']-(.5*np.sum((a-y)**2)+sum(abs(d2(a)))))<1e-10
    checks.append('L1 3 paths equal prior scalar implementation, objective/gap verified')
    n=700;c=100*np.exp(np.cumsum(rng.normal(0,.02,n)));o=c*np.exp(rng.normal(0,.005,n));h=np.maximum(c,o)*1.01;l=np.minimum(c,o)*.99;v=rng.uniform(100,10000,n)
    z=dict(close=c,open=o,high=h,low=l,volume=v);f,names,ctx,atr=calculate(z)
    for t in [100,200,350,600]:
        ff,nn,cc,aa=calculate({k:x[:t] for k,x in z.items()})
        assert names==nn and np.array_equal(ff,f[:t]) and np.array_equal(cc,ctx[:t])
    checks.append(f'all {len(names)} features prefix invariant at 4 cutoffs')
    # Standalone textbook computations for RSI60, MACD and Bollinger event dates.
    import pandas as pd
    gain=np.zeros(n);loss=np.zeros(n);rr=np.full(n,np.nan);dc=np.diff(c)
    gain[14]=np.mean(np.maximum(dc[:14],0));loss[14]=np.mean(np.maximum(-dc[:14],0))
    for t in range(14,n):
        if t>14:gain[t]=(gain[t-1]*13+max(dc[t-1],0))/14;loss[t]=(loss[t-1]*13+max(-dc[t-1],0))/14
        rr[t]=100*gain[t]/(gain[t]+loss[t])
    manual=np.array([int(rr[t]<60 and rr[t-1]>=60) for t in range(n)])
    assert np.array_equal(manual[65:],f[65:,names.index('rsi60')])
    for t in range(65,n):
        band=np.mean(c[t-19:t+1])+2*np.std(c[t-19:t+1]);prior=np.mean(c[t-20:t])+2*np.std(c[t-20:t])
        assert f[t,names.index('bb_upper_reentry')]==int(c[t]<band and c[t-1]>=prior)
    checks.append('RSI and Bollinger independent scalar recomputation: 635 bars')
    assert np.isnan(cross(np.array([np.nan,2.,1.,0.]),1.5)[1])
    assert cross(np.array([2.,1.5,1.]),1.5)[2]==1
    fit=np.array([0.,1.,2.,1.,0.,1.,2.,1.,0.]);seg=np.zeros(9)
    starts,ends,_=structure(fit,seg);assert starts.tolist()==[2] and ends.tolist()==[4]
    checks.append('cross equality, missing input, completed/censored L1 boundaries')
    ff=np.array([[0,0],[1,-1],[0,0],[1,1],[0,0]],np.int8);w=window(ff,-1,1)
    assert w[1].tolist()==[1,-1] and w[3].tolist()==[1,1] and (w[0]==-1).all()
    checks.append('event-window missing and edge handling')
    OUT.mkdir(parents=True,exist_ok=True);write(OUT/'verification-synthetic.json',dict(status='PASS',checks=checks))
    print(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=False))

if __name__=='__main__':main()
