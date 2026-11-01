"""Unchanged numeric primitives/boundaries from a8fa907; no market/solver imports."""
from pathlib import Path
import numpy as np
import pandas as pd
import hashlib,json,tempfile,os

def roll(x, n, how='mean'):
    return getattr(pd.Series(x).rolling(n), how)().to_numpy()

def lag(x, n=1):
    return np.r_[np.full(min(n,len(x)),np.nan),x[:-n]] if n<len(x) else np.full(len(x),np.nan)

def ema(x,n):
    return pd.Series(x).ewm(span=n,adjust=False,min_periods=n).mean().to_numpy()

def wilder(x,n):
    out=np.full(len(x),np.nan)
    for i in range(n-1,len(x)):
        if i and np.isfinite(out[i-1]):out[i]=(out[i-1]*(n-1)+x[i])/n
        elif np.isfinite(x[i-n+1:i+1]).all():out[i]=np.mean(x[i-n+1:i+1])
    return out

def ratio(a,b):
    return np.divide(a,b,out=np.full(np.broadcast(a,b).shape,np.nan),where=np.isfinite(b)&(b!=0))

def cross(a,b):
    a=np.asarray(a);b=np.broadcast_to(b,a.shape)
    tol=1e-12*np.maximum(abs(a),abs(b));diff=a-b
    ok=np.isfinite(a)&np.isfinite(b)&np.isfinite(lag(a))&np.isfinite(lag(b))
    return np.where(ok,(diff < -tol)&(lag(diff)>=-lag(tol)),np.nan)

def new_state(x):
    return np.where(np.isfinite(x)&np.isfinite(lag(x)),(x==1)&(lag(x)!=1),np.nan)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_arrays(path,**arrays):
    path=Path(path);fd,temp=tempfile.mkstemp(prefix=path.stem+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            np.savez_compressed(stream,**arrays);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)

def structure(fit,seg):
    slope=np.r_[np.diff(fit),np.nan];slope[np.r_[seg[1:]!=seg[:-1],True]]=np.nan
    down=np.isfinite(slope)&(slope < -1e-6)
    starts=np.flatnonzero(down&~np.r_[False,down[:-1]]);ends=np.flatnonzero(down&~np.r_[down[1:],False])+1
    # A run touching an unknown edge is censored, not a completed short decline.
    good=(starts>0)&np.isfinite(slope[np.maximum(starts-1,0)])&np.isfinite(slope[np.minimum(ends,len(slope)-1)])
    return starts[good],ends[good],slope

def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,path)
