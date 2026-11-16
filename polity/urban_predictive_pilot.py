"""Train-only mean and inner-province predictive dispersion for a fixed pilot."""
import numpy as np


def nested_fit(X,y,fold,eligible,outer):
    X,y,fold,eligible=np.asarray(X,float),np.asarray(y,float),np.asarray(fold),np.asarray(eligible,bool)
    if X.ndim!=2 or any(a.shape!=(len(X),) for a in [y,fold,eligible]):raise ValueError('Design shape mismatch')
    if not np.isfinite(X).all() or not np.isfinite(y).all() or outer not in range(4):raise ValueError('Invalid design')
    tr=eligible & (fold!=outer)
    def fit(mask):
        if mask.sum()<10 or np.linalg.matrix_rank(X[mask])<X.shape[1]:raise ValueError('Insufficient training support')
        return np.linalg.lstsq(X[mask],y[mask],rcond=None)[0]
    residual=[];inner=[]
    for held in range(4):
        if held==outer:continue
        training=tr & (fold!=held);testing=tr & (fold==held)
        if not testing.any():raise ValueError('Empty inner fold')
        beta=fit(training);r=y[testing]-X[testing]@beta
        residual.extend(r);inner.append(dict(heldout=held,training_rows=int(training.sum()),test_rows=int(testing.sum()),coefficients=beta.tolist(),squared_error=float(r@r)))
    sigma=float(np.sqrt(np.mean(np.square(residual))))
    if not np.isfinite(sigma) or sigma<=0:raise ValueError('Nonpositive predictive sigma')
    return fit(tr),sigma,inner
