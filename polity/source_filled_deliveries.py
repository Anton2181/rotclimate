"""Join fixed physical collector jobs to their raw source withdrawals by ID."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SourceFilledDeliveries:
    raw_requested: np.ndarray
    raw_withdrawn: np.ndarray
    raw_unfilled: np.ndarray
    retained_packed_potential: np.ndarray
    retained_source_filled: np.ndarray
    retained_unfilled_potential: np.ndarray


def source_filled_deliveries(job_ids,job_raw_cargo,source_ids,source_requested,source_withdrawn,source_unfilled,*,retention=.95):
    """Match every request once. Retention is applied here to RAW source cargo.

    Missing potential is a counterfactual destination amount, not an actual
    transport loss on grain that never left its source export store.
    """
    job_ids,source_ids=np.asarray(job_ids),np.asarray(source_ids)
    if any(v.ndim!=1 or v.dtype.kind not in 'iu' for v in (job_ids,source_ids)):
        raise ValueError('One-dimensional integer job and source IDs required')
    if any(np.any(v<0) or len(np.unique(v))!=len(v) for v in (job_ids,source_ids)):
        raise ValueError('Job and source IDs must be unique and nonnegative')
    if len(job_ids)!=len(source_ids) or not np.array_equal(np.sort(job_ids),np.sort(source_ids)):
        raise ValueError('Source withdrawals must match every fixed physical job exactly')
    raw,requested,withdrawn,unfilled=[np.asarray(v,float) for v in (job_raw_cargo,source_requested,source_withdrawn,source_unfilled)]
    if raw.shape!=job_ids.shape or any(v.shape!=source_ids.shape for v in (requested,withdrawn,unfilled)):
        raise ValueError('Each job/source ID requires its raw cargo fields')
    if any(not np.isfinite(v).all() or np.any(v<0) for v in (raw,requested,withdrawn,unfilled)):
        raise ValueError('Raw cargo must be finite and nonnegative')
    if not np.isfinite(retention) or not 0<=retention<=1:
        raise ValueError('Transport retention must lie in [0,1]')
    if np.any(withdrawn>requested) or np.any(abs(withdrawn+unfilled-requested)>1e-12*np.maximum(1.,requested)):
        raise ValueError('Actual source withdrawals and unfilled requests must partition raw demand')
    order=np.argsort(source_ids);lookup=order[np.searchsorted(source_ids[order],job_ids)]
    if not np.array_equal(requested[lookup],raw):
        raise ValueError('Changed source or physical-job raw cargo')
    taken=withdrawn[lookup].copy();missing=unfilled[lookup].copy()
    return SourceFilledDeliveries(raw.copy(),taken,missing,raw*retention,taken*retention,missing*retention)
