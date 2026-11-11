"""Explicit versus documented parent-scope dates; values are never imputed."""
from polity.institution_evidence import time_evidence


def group_scopes(rows,parent_start,parent_end,policy):
    if policy not in ('explicit_only','documented_parent_scope'):raise ValueError('Unknown source-time policy')
    rows=list(rows);parent=time_evidence(parent_start,parent_end)
    dated=[r['year_from'] is not None or r['year_to'] is not None for r in rows]
    group_reason=None
    if policy=='documented_parent_scope':
        if any(dated) and not all(dated):group_reason='mixed_time_scope_review'
        elif rows and not any(dated) and len(rows)>1 and not any(r.get(k) is True for r in rows for k in ['is_disputed','is_uncertain']):
            group_reason='ambiguous_multiple_undated'
    result=[]
    for row,is_dated in zip(rows,dated):
        start,end=row['year_from'],row['year_to'];raw=time_evidence(start,end)
        scope=None;reason=None;lo=hi=None
        if parent['state']!='ordered_exported_interval':reason='invalid_parent_interval'
        elif group_reason:reason=group_reason
        elif policy=='documented_parent_scope' and not is_dated:
            lo,hi=parent_start,parent_end;scope='documented_parent_scope'
        elif start is None and end is None:reason='missing_explicit_interval'
        elif start is None or end is None:reason='partial_date_review'
        elif raw['state']!='ordered_exported_interval':reason=raw['state']
        elif start<parent_start or end>parent_end:reason='outside_parent_interval'
        else:lo,hi=start,end;scope='explicit_interval'
        result.append(dict(raw_from=start,raw_to=end,scope=scope,review_reason=reason,
            effective_from=lo,effective_to=hi,eligible=scope is not None,
            compatible_with_positive_year200=(lo<=200<=hi) if scope else None,
            zero_year_present=raw['zero_year_present'] or parent['zero_year_present'],calendar_harmonized=False))
    return result
