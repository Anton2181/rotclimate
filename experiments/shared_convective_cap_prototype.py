"""Offline hypothesis: one existing cap for both convective rain enhancements.

No production imports, field updates, coupled integration or accuracy claim.
"""
import numpy as np
DAY=86400.


def shared_cap_components(water,saturation,dynamics,instability,threshold,tau_days,
                          raw_convection,cap,subcloud_survival):
    """Return hypothetical mm/day components at a FIXED saved model state.

    Ordinary humidity/dynamics rain remains. Its warm-instability enhancement
    and explicit exponential convection share one cap. The existing rate law's
    max(W,.1) conversion is retained, including near-zero-water behavior. With
    no cap, preserve both legacy enhancement terms; this is not a global scale.
    """
    W,Ws,A,I,C,K,F=np.broadcast_arrays(water,saturation,dynamics,instability,raw_convection,cap,subcloud_survival)
    if not all(np.isfinite(v).all() for v in [W,Ws,A,I,C,K,F]) or (W<0).any() or (Ws<=0).any() or (I<0).any() or tau_days<=0:
        raise ValueError('Need finite physical column inputs')
    gate=np.clip((W/Ws-threshold)/(1-threshold),0,2)**1.5
    base_rate=A*gate*np.minimum(I,1)/(tau_days*DAY)
    enhancement_rate=A*gate*np.maximum(I-1,0)/(tau_days*DAY)
    equivalent=np.maximum(W,.1)
    enhancement_mm=enhancement_rate*equivalent*DAY
    combined=enhancement_mm+C
    total_convective=np.where(K>0,K*np.tanh(combined/np.maximum(K,1e-9)),combined)
    convective=total_convective/(equivalent*DAY)*W*DAY
    base=base_rate*W*DAY
    overflow=np.maximum(W-Ws,0)
    return dict(base=base*F,convective=convective*F,overflow=overflow,
        pre_subcloud_convective_mm_day=convective,
        pre_subcloud_cap_mm_day=K*W/equivalent,
        total_rain=(base+convective)*F+overflow)
