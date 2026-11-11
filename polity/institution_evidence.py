"""Preserve source uncertainty and intervals without inventing staff quantities."""
import math

PRESENCE_CODES={'P':'coded_present','A':'coded_absent','IP':'inferred_present',
    'IA':'inferred_absent','SU':'suspected_unknown','U':'expert_unknown'}


def value_evidence(lower,upper):
    """Retain API codes/ranges; unsupported codes are review items, not absence."""
    result=dict(raw_from=lower,raw_to=upper)
    if lower is None and upper is None:state='missing_export_value'
    elif isinstance(lower,str) and upper is None:state=PRESENCE_CODES.get(lower,'unresolved_code')
    elif all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in [lower,upper]):
        state='reversed_numeric_bounds' if lower>upper else 'numeric_point' if lower==upper else 'numeric_interval'
    else:state='unresolved_value_shape'
    return dict(result,state=state)


def time_evidence(start,end):
    """Signed exported-year bounds, with no nearest-date rescue or BCE rewrite."""
    valid=lambda x:isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and int(x)==x
    state=('missing_time_bounds' if start is None or end is None else 'invalid_time_bounds' if not valid(start) or not valid(end)
           else 'reversed_time_bounds' if start>end else 'ordered_exported_interval')
    return dict(raw_from=start,raw_to=end,state=state,zero_year_present=start==0 or end==0,
        compatible_with_positive_year200=(start<=200<=end) if state=='ordered_exported_interval' else None,
        calendar_harmonized=False)
