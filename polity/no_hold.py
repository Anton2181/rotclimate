"""One funded whole leg, with charge annotations that add neither grain nor time.

Funding and the whole-leg delivered amount are supplied by the upstream ledger.
Event labels do not identify stores, allocate capacity or establish access rights.
"""
from dataclasses import dataclass
import math

import numpy as np


def _copy(value):
    result=np.array(value,copy=True)
    result.flags.writeable=False
    return result


@dataclass(frozen=True)
class NoHoldBatch:
    ids: tuple
    origin: np.ndarray
    destination: np.ndarray
    sent: np.ndarray
    delivered: np.ndarray
    departure_bin: np.ndarray
    arrival_bin: np.ndarray
    charge_labels: tuple
    charges: np.ndarray
    remaining_after_charge: np.ndarray
    whole_leg_charge: np.ndarray
    residual: np.ndarray


class NoHoldLedger:
    """Reject repeated consignment IDs across calls; failed batches claim no IDs."""
    def __init__(self):
        self._seen=set()
        self._totals=[]
        self.record_calls=0

    def record(self,ids,origin,destination,sent,delivered,departure_bin,arrival_bin,*,
               event_labels=(),charge_allocation=None,hold_bins=0):
        if isinstance(ids,(str,bytes)):raise ValueError('Explicit consignment ID sequence required')
        ids=tuple(ids);n=len(ids)
        if any(not isinstance(v,str) or not v.strip() for v in ids):raise ValueError('Nonempty named consignment IDs required')
        if len(set(ids))!=n or self._seen.intersection(ids):raise ValueError('Duplicate consignment funding')
        endpoints=[np.asarray(v) for v in [origin,destination]]
        if any(v.shape!=(n,) or v.dtype.kind not in 'iu' or (v<0).any() or (v>np.iinfo(np.intp).max).any() for v in endpoints):
            raise ValueError('Nonnegative integer physical endpoint IDs required')
        bins=[np.asarray(v) for v in [departure_bin,arrival_bin]]
        if any(v.shape!=(n,) or v.dtype.kind not in 'iu' or (v<0).any() or (v>=12).any() for v in bins):
            raise ValueError('Explicit integer monthly bins in zero through eleven required')
        departure,arrival=[v.astype(np.intp) for v in bins]
        hold=np.asarray(hold_bins)
        if hold.shape!=() or hold.dtype.kind not in 'iu' or hold.item()!=0:
            raise ValueError('Only zero hold supported;positive holding needs a separate storage contract')
        if np.any(arrival!=(departure+1)%12):raise ValueError('Zero hold must preserve original one-bin endpoint arrival')
        sent=np.asarray(sent,float);delivered=np.asarray(delivered,float)
        if any(v.shape!=(n,) or not np.isfinite(v).all() or (v<0).any() for v in [sent,delivered]):
            raise ValueError('Aligned finite nonnegative funded amounts required')
        if np.any(delivered>sent):raise ValueError('Endpoint delivery exceeds funded grain')
        charge=sent-delivered
        if isinstance(event_labels,(str,bytes)):raise ValueError('Explicit ordered charge-event labels required')
        labels=tuple(event_labels)
        if any(not isinstance(v,str) or not v.strip() for v in labels) or len(set(labels))!=len(labels):
            raise ValueError('Unique nonempty charge-event labels required')
        if not labels:
            if charge_allocation is not None:raise ValueError('Charge allocation requires explicit event labels')
            labels=('whole-leg charge',);allocation=charge[None,:]
        else:
            if charge_allocation is None:raise ValueError('Event charges must be supplied explicitly')
            allocation=np.asarray(charge_allocation,float)
        if allocation.shape!=(len(labels),n) or not np.isfinite(allocation).all() or np.any(allocation<0):
            raise ValueError('Aligned finite nonnegative charge allocation required')
        cumulative=np.cumsum(allocation,axis=0)
        if np.any(cumulative>sent[None,:]):raise ValueError('Charge events overdraw funded grain')
        residual=charge-allocation.sum(0)
        tolerance=1e-10*np.maximum(1,np.maximum(sent,delivered))
        if np.any(abs(residual)>tolerance):raise ValueError('Event charges must sum to existing whole-leg charge')
        result=NoHoldBatch(ids,*[_copy(v) for v in endpoints],_copy(sent),_copy(delivered),
            _copy(departure),_copy(arrival),labels,_copy(allocation),_copy(sent[None,:]-cumulative),_copy(charge),_copy(residual))
        self._seen.update(ids);self.record_calls+=1
        self._totals.append((math.fsum(sent),math.fsum(delivered),math.fsum(charge)))
        return result

    def summary(self):
        sent,delivered,charged=[math.fsum(row[i] for row in self._totals) for i in range(3)]
        return dict(consignments=len(self._seen),record_calls=self.record_calls,sent_kcal=sent,
            delivered_kcal=delivered,whole_leg_charge_kcal=charged,
            residual_kcal=sent-math.fsum([delivered,charged]),event_funding_kcal=0,
            inferred_physical_duration=False,inferred_capacity=False,inferred_rights=False)
