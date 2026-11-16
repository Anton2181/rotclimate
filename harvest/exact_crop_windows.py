"""Exact-energy alternatives of the original Earth single-crop window rule.

No yield tolerance or probabilistic interpretation: candidate energy must equal
the full-precision maximum. Earliest/latest describe calendar-year boundaries,
not bounds on the response of a food network.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class ExactWindows:
    energy: np.ndarray
    first_masks: np.ndarray
    first_eligible: np.ndarray
    boundary_bits: np.ndarray
    window_count: np.ndarray
    earliest_masks: np.ndarray
    latest_masks: np.ndarray
    earliest_boundary: np.ndarray
    latest_boundary: np.ndarray


def select_exact_windows(energies,windows,forbidden):
    energies=np.asarray(energies);forbidden=np.asarray(forbidden,bool)
    if energies.ndim!=2 or len(windows)!=len(energies) or forbidden.shape!=(12,energies.shape[1]):
        raise ValueError('Window×source energies and twelve aligned forbidden bins required')
    if not np.isfinite(energies).all() or np.any(energies<0):raise ValueError('Finite nonnegative window energies required')
    for start,length in windows:
        if not 0<=start<12 or not 1<=length<12:raise ValueError('Contiguous cyclic growing windows required')
    best=energies.max(0);positive=best>0;choice=energies.argmax(0)
    first=np.zeros(forbidden.shape,bool);early=first.copy();late=first.copy()
    early_boundary=np.full(len(best),-1,np.int8);late_boundary=early_boundary.copy()
    bits=np.zeros(len(best),np.uint16);count=np.zeros(len(best),np.uint16)
    for i,((start,length),energy) in enumerate(zip(windows,energies)):
        months=[(start+k)%12 for k in range(length)];boundary=(start+length)%12
        original=positive&(choice==i)
        for month in months:first[month,original]=True
        tied=positive&(energy==best)&~forbidden[months].any(0)
        bits|=np.where(tied,1<<boundary,0).astype(np.uint16);count+=tied
        earlier=tied&((early_boundary<0)|(boundary<early_boundary))
        later=tied&((late_boundary<0)|(boundary>late_boundary))
        early[:,earlier]=False;late[:,later]=False
        for month in months:early[month,earlier]=True;late[month,later]=True
        early_boundary[earlier]=boundary;late_boundary[later]=boundary
    if np.any(positive&(bits==0)):raise ValueError('Positive crop maximum has no eligible equal-energy window')
    return ExactWindows(best,first,~(first&forbidden).any(0),bits,count,early,late,early_boundary,late_boundary)


def exact_crop_windows(T,P,PET,S0,irr,crop,*,forbidden=None):
    # Preserve original float32 T/P/irrigation arithmetic, including 1.0-irr.
    T,P,PET,S0,irr=[np.asarray(a) for a in [T,P,PET,S0,irr]]
    if T.ndim!=2 or T.shape[0]!=12 or any(a.shape!=T.shape for a in [P,PET,S0]) or irr.shape!=T.shape[1:]:
        raise ValueError('Original twelve-bin crop-source arrays required')
    if not all(np.isfinite(a).all() for a in [T,P,PET,S0,irr]) or np.any((irr<0)|(irr>1)):
        raise ValueError('Finite climate/soil fields and valid irrigation shares required')
    forbidden=np.zeros(T.shape,bool) if forbidden is None else np.asarray(forbidden,bool)
    energies=[];windows=[]
    for length in range(crop['months'][0],crop['months'][1]+1):
        for start in range(12):
            idx=[(start+k)%12 for k in range(length)];Ts,Ps,Es=T[idx],P[idx],PET[idx]
            lo,hi=crop['window']
            ok=np.all((Ts>=lo)&(Ts<=hi),axis=0)&(Ts.max(0)>=crop['need_warm'])
            heat=np.sum(np.maximum(Ts-crop['base'],0.),axis=0)*(365./12)
            ok&=heat>=crop['heat']
            etc=crop['kc']*Es.sum(0)+crop.get('flood_mm',0.)
            supply=.8*Ps.sum(0)+S0[idx[0]]
            fw=np.clip(supply/np.maximum(etc,1.),0.,1.)
            t=np.clip((fw-.3)/(.5-.3),0.,1.)
            yf=np.clip(1.-crop['ky']*(1.-fw),0.,1.)*(t*t*(3.-2.*t))
            yf=irr+(1.-irr)*yf
            energy=np.where(ok,yf,0.)*crop['grain']*1000.*crop['edible']*crop['kcal']*(1-crop['seed'])
            energies.append(energy);windows.append((start,length))
    return select_exact_windows(np.array(energies),windows,forbidden)
