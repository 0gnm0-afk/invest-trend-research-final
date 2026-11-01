"""Frozen union: original61 plus11 additional conditions, per market."""
from pathlib import Path
import hashlib
import numpy as np
import old_signals,new_signals
from legacy import sha

SELECTED={'KR':['rsi30','mfi20'],'US':['rsi30','cci-100']}
NEW=['supertrend','psar','trix_zero','trix_signal','stochrsi20','stochrsi_cross','rmi30','rmi50','chaikin','avwap_quarter','volume_osc']
_META={}

def code_hash():
    here=Path(__file__).resolve().parent
    return hashlib.sha256(''.join(sha(here/k) for k in ['features.py','old_signals.py','new_signals.py','legacy.py']).encode()).hexdigest()

def _segment(z,market):
    base,ids,ctx,atr,cv,_=old_signals.calculate(z)
    zz=dict(z,segment=np.zeros(len(base),int))
    full,meta=old_signals.extras(zz,base,ids,SELECTED[market])
    newer,ni,*_=new_signals.calculate(z)
    meta += [new_signals.META[k] for k in NEW]
    full=np.column_stack([full,newer[:,[ni.index(k) for k in NEW]]])
    assert len(meta)==72 and len(set(b['id'] for b in meta))==72
    return full,meta,cv,ctx,atr

def metadata(market):
    if market not in _META:
        # extras imports study.extensions; supply it without recursive import at startup.
        import sys
        mod=sys.modules.get('study') or sys.modules.get('__main__')
        if not hasattr(mod,'extensions'):
            from followups import extensions
            mod.extensions=extensions
        sys.modules.setdefault('study',mod)
        z={k:np.full(210,100.) for k in ['close','open','high','low','volume']}
        z['date']=(np.datetime64('2000-01-01')+np.arange(210)).astype(str)
        _META[market]=_segment(z,market)[1]
    return _META[market]

def calculate(z,market):
    n=len(z['date']);meta=metadata(market)
    f=np.full((n,len(meta)),-1,np.int8);cv=np.full((n,7),np.nan);ctx=np.zeros((n,3),np.int8);atr=np.full(n,np.nan)
    for g in np.unique(z['segment']):
        ix=np.flatnonzero(z['segment']==g)
        if len(ix)<80:continue
        a,_,v,c,t=_segment({k:z[k][ix] for k in ['close','open','high','low','volume','date']},market)
        f[ix]=a;cv[ix]=v;ctx[ix]=c;atr[ix]=t
    return f,meta,cv,ctx,atr
