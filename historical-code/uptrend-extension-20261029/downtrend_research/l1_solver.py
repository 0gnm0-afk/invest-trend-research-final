import numpy as np
from scipy.linalg import solveh_banded

# Same dual interior-point objective as the prior session. Only the linear
# system solver is accelerated; scalar implementation retained for verification.
def fast_pentasolve(diagonal, rhs):
    ab = np.zeros((3, len(rhs)))
    ab[0] = diagonal
    ab[1, :-1] = -4
    ab[2, :-2] = 1
    return solveh_banded(ab, rhs, lower=True, check_finite=False)

def d2(x):
    return x[:-2] - 2*x[1:-1] + x[2:]

def dt(u):
    x = np.zeros(len(u)+2)
    x[:-2] += u
    x[1:-1] -= 2*u
    x[2:] += u
    return x

def pentasolve(diagonal, rhs):
    """Solve SPD pentadiagonal system with off-diagonals -4 and +1."""
    n = len(rhs)
    ld = np.empty(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    for i in range(n):
        if i > 1:
            l2[i] = 1/ld[i-2]
        if i:
            l1[i] = (-4 - l2[i]*l1[i-1])/ld[i-1]
        v = diagonal[i] - l1[i]**2 - l2[i]**2
        if v <= 0:
            raise ArithmeticError(('nonpositive Cholesky pivot', i, v))
        ld[i] = np.sqrt(v)
    z = np.empty(n)
    for i in range(n):
        z[i] = (rhs[i] - (l1[i]*z[i-1] if i else 0)
                - (l2[i]*z[i-2] if i > 1 else 0))/ld[i]
    x = np.empty(n)
    for i in range(n-1, -1, -1):
        x[i] = (z[i] - (l1[i+1]*x[i+1] if i+1 < n else 0)
                - (l2[i+2]*x[i+2] if i+2 < n else 0))/ld[i]
    return x

def l1trend(y, lam, tol=1e-6, scalar=False):
    offset = float(np.mean(y))
    y = np.asarray(y, float)-offset
    dy = d2(y)
    u = np.zeros(len(dy))
    mu = 1.0
    iterations = 0
    for outer in range(23):
        for _ in range(100):
            r = dt(u)
            au = d2(r)
            left, right = lam-u, lam+u
            g = au-dy + mu*(1/left - 1/right)
            h = 6 + mu*(1/left**2 + 1/right**2)
            step = (pentasolve if scalar else fast_pentasolve)(h, -g)
            dec = -float(g@step)
            if dec < 1e-13:
                break
            alpha = 1.0
            pos, neg = step > 0, step < 0
            if np.any(pos):
                alpha = min(alpha, .99*float(np.min(left[pos]/step[pos])))
            if np.any(neg):
                alpha = min(alpha, .99*float(np.min(-right[neg]/step[neg])))
            f = .5*(r@r)-dy@u-mu*np.sum(np.log(left)+np.log(right))
            for _ in range(60):
                v = u+alpha*step
                rv = dt(v)
                fv = .5*(rv@rv)-dy@v-mu*np.sum(np.log(lam-v)+np.log(lam+v))
                if fv <= f-.01*alpha*dec:
                    break
                alpha *= .5
            else:
                raise ArithmeticError('Newton line search failed')
            u = v
            iterations += 1
        x = y-dt(u)
        gap = float(np.sum(lam*np.abs(d2(x))-u*d2(x)))
        if gap < tol:
            primal = .5*np.sum((y-x)**2)+lam*np.sum(np.abs(d2(x)))
            return x+offset, {'primal_dual_gap': gap, 'iterations': iterations,
                              'objective': float(primal), 'max_dual_abs': float(np.max(np.abs(u)))}
        mu *= .15
    raise ArithmeticError(('L1 solver did not converge', lam, gap))
