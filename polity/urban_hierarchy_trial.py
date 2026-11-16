"""Training-isolated conditional-site hierarchy trial, not an adopted map law."""
import numpy as np

from polity.urban_predictive_pilot import nested_fit
from polity.settlement_sizes import draws,generate_area


def closed_pairs(centre,fold,outer,training=False):
    centre=np.asarray(centre);fold=np.asarray(fold);valid=np.flatnonzero(centre>=0)
    mask=np.zeros(len(centre),bool)
    if training:mask[valid]=(fold[valid]!=outer)&(fold[centre[valid]]!=outer)
    else:mask[valid]=(fold[valid]==outer)&(fold[centre[valid]]==outer)
    return mask


def member_order(centre,capital):
    rng=np.random.default_rng(2026)
    return {int(c):rng.permutation(np.flatnonzero(centre==c)) for c in np.flatnonzero(capital)}


def generate(mean,sigma,capital,order,phi,shift,seed,bounds,return_residual=False):
    e=draws(len(mean),seed).copy()
    for c,members in order.items():
        pool=np.r_[c,members[:int(round(phi*len(members)))]]
        j=pool[np.argmax(e[pool])];e[c],e[j]=e[j],e[c]
    area=generate_area(mean+shift*capital,sigma,e,*bounds)
    return (area,e) if return_residual else area


def hierarchy_stats(area,mean,capital_mask,pair_mask,centre):
    if not capital_mask.any() or not pair_mask.any():raise ValueError('Capital and closed-pair support required')
    ratio=area[pair_mask]/area[centre[pair_mask]]
    return np.array([np.mean(ratio>1),np.median(ratio),np.exp(np.mean(np.log(area[capital_mask])-mean[capital_mask]))])


def fit_fold(lnH,y,fold,capital,centre,outer,*,seeds=(1,7,19,43,97),phis=(0,.25,.5,.75,1),shifts=tuple(round(i*.1,1) for i in range(14)),bounds=(1.,1782.9999999999995)):
    lnH,y,fold,capital,centre=np.asarray(lnH),np.asarray(y),np.asarray(fold),np.asarray(capital,bool),np.asarray(centre)
    X=np.column_stack([np.ones(len(y)),lnH]);training=fold!=outer
    beta,sigma,inner=nested_fit(X,y,fold,np.ones(len(y),bool),outer)
    final_mean=X@beta;selection_mean=final_mean.copy()
    for receipt in inner:
        use=training & (fold==receipt['heldout']);selection_mean[use]=X[use]@np.array(receipt['coefficients'])
    pairs=closed_pairs(centre,fold,outer,training=True);caps=capital & training
    truth=np.ones(len(y));truth[training]=np.exp(y[training])
    observed=hierarchy_stats(truth,selection_mean,caps,pairs,centre);order=member_order(centre,capital)
    candidates=[]
    for phi in phis:
        for shift in shifts:
            values=np.mean([hierarchy_stats(generate(selection_mean,sigma,capital,order,phi,shift,s,bounds),selection_mean,caps,pairs,centre) for s in seeds],axis=0)
            loss=float((values[0]-observed[0])**2+np.log(values[1]/observed[1])**2+np.log(values[2]/observed[2])**2)
            candidates.append(dict(phi=float(phi),shift=float(shift),loss=loss,modeled=values.tolist()))
    best=min(candidates,key=lambda c:(c['loss'],c['phi'],c['shift']))
    ensemble=np.array([generate(final_mean,sigma,capital,order,best['phi'],best['shift'],s,bounds) for s in seeds])
    receipt=dict(outer=outer,training_records=int(training.sum()),training_pairs=int(pairs.sum()),training_capitals=int(caps.sum()),coefficients=beta.tolist(),sigma=sigma,
                 selected_phi=best['phi'],selected_shift=best['shift'],selected_loss=best['loss'],observed_training=observed.tolist(),inner=inner)
    return ensemble,final_mean,receipt,candidates


def ensemble_scores(areas,truth):
    z=np.log(areas);y=np.log(truth);m=np.median(z,axis=0);r=y-m
    crps=np.mean(np.abs(z-y),axis=0)-.5*np.mean(np.abs(z[:,None,:]-z[None,:,:]),axis=(0,1))
    return dict(n=len(y),log_area_crps=float(np.mean(crps)),median_log_area_mae=float(np.mean(np.abs(r))),median_log_area_rmse=float(np.sqrt(np.mean(r*r))))
