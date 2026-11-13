"""Cyclic flood/crop phase diagnostics, not a water-volume irrigation model."""
import numpy as np


def crop_flood_timing(monthly_flow, *, crop_months=5, lead_months=3):
    """Pre-sowing and standing-crop shares of above-mean monthly discharge.

    Axis0 is January..December. Output axis0 gives every possible sowing month.
    Zero/constant flow has no seasonal flood opportunity. Flow units cancel;
    these fractions must not be interpreted as irrigable area or water volume.
    """
    q=np.asarray(monthly_flow,dtype=float)
    if q.ndim<1 or q.shape[0]!=12 or not np.isfinite(q).all() or np.any(q<0):
        raise ValueError('Twelve finite nonnegative monthly mean flows required')
    for value in (crop_months,lead_months):
        if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=12:
            raise ValueError('Crop and lead windows require integer months in1..12')
    if crop_months+lead_months>12:
        raise ValueError('Pre-sowing and standing crop windows must not overlap')
    # Scaling first avoids overflow when inputs approach floating-point limits.
    maximum=q.max(axis=0);scaled=np.divide(q,maximum,out=np.zeros_like(q),where=maximum>0)
    excess=np.maximum(scaled-scaled.mean(axis=0),0.);total=excess.sum(axis=0)
    pre=[];standing=[]
    for sow in range(12):
        before=excess[[(sow-d)%12 for d in range(1,lead_months+1)]].sum(axis=0)
        during=excess[[(sow+d)%12 for d in range(crop_months)]].sum(axis=0)
        pre.append(np.divide(before,total,out=np.zeros_like(total),where=total>0))
        standing.append(np.divide(during,total,out=np.zeros_like(total),where=total>0))
    pre,standing=np.clip(pre,0.,1.),np.clip(standing,0.,1.)
    return dict(pre_sowing_excess_share=pre,standing_crop_excess_share=standing,
                compatibility=np.maximum(0.,pre-standing),seasonal_excess_present=total>0)
