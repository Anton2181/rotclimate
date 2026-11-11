"""Source change dates and conservative validation blocks, never dated roles.

The rural-Britain methodology allows successive functions under one record.
Consistent change dates do not identify which role changed or prove continuity.
"""
from dataclasses import dataclass
import math

from .role_evidence import association_blocks


def numeric(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):return None


@dataclass(frozen=True)
class ChangeEvidence:
    status: str
    recorded_changes: tuple[float | None, ...]
    flags: tuple[str, ...]
    usable_for_change_order: bool
    role_intervals_assigned: bool = False


def change_evidence(start,end,phase1,phase2):
    """Audit source order and envelope without sorting, clipping or role dating."""
    a,b=numeric(start),numeric(end);points=[];flags=set()
    if a is None or b is None:flags.add('unknown_site_span')
    elif a>b:flags.add('inverted_site_span')
    elif a==0 or b==0:flags.add('ambiguous_zero_site_endpoint')
    present=[value is not None and bool(str(value).strip()) for value in [phase1,phase2]]
    for index,value in enumerate([phase1,phase2],1):
        if not present[index-1]:continue
        point=numeric(value);points.append(point)
        if point is None:flags.add('nonnumeric_change_date')
        elif point==0:flags.add('ambiguous_zero_change_date')
        elif a is not None and b is not None and not a<=point<=b:flags.add('change_outside_recorded_span')
    if present[1] and not present[0]:flags.add('second_change_without_first')
    if len(points)==2 and None not in points:
        if points[0]>points[1]:flags.add('reversed_change_order')
        elif points[0]==points[1]:flags.add('coincident_change_dates')
    blocking=flags-{'coincident_change_dates'}
    usable=bool(points) and not blocking
    state='no_recorded_changes' if not points else 'consistent_changes' if usable else 'changes_require_review'
    return ChangeEvidence(state,tuple(points),tuple(sorted(flags)),usable)


def review_blocks(core,associations):
    """Extend exact-association blocks with exact location/name evidence.

    core rows: (record_id, county, site_name, easting, northing).
    Equal points or county+name block folds together, but retain distinct source
    observations. Neither condition proves one residential nucleus or occupation.
    """
    ids=[r[0] for r in core]
    if len(ids)!=len(set(ids)):raise ValueError('Unique source record IDs required')
    extra=[]
    for record,county,name,east,north in core:
        e,n=numeric(east),numeric(north)
        if e is not None and n is not None:
            extra.append((record,'__review_exact_XY__','',f'{e:.17g},{n:.17g}'))
        county,name=(' '.join(str(v or '').casefold().split()) for v in [county,name])
        if county and name:extra.append((record,'__review_county_name__',county,name))
    return association_blocks(ids,list(associations)+extra)
