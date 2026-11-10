"""Observation units for role calibration, separate from places and residents.

An evidence channel is neither an occupied settlement nor a staffed institution.
Association components block related observations from crossing validation folds;
they deliberately do not merge the underlying physical places.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RoleEvidence:
    record_id: str
    channels: tuple[str, ...]
    unknown_labels: tuple[str, ...]
    site_time: str
    date_flags: tuple[str, ...]
    role_time: str = 'undated'
    physical_place: str | None = None


def occupation_window(start, end, year=200):
    """Classify span compatibility, not occupation probability or feature dates.

    -100/400 censoring conventions are specific to the rural-Britain source.
    Zero endpoints remain ambiguous; no automatic conversion to an era boundary.
    """
    def numeric(value):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (ValueError, TypeError):
            return None
    a, b, target = numeric(start), numeric(end), numeric(year)
    if target is None:
        raise ValueError('Finite target year required')
    flags = []
    if a == -100:
        flags.append('start_left_censored')
    if b == 400:
        flags.append('end_period_convention')
    if a == 0 or b == 0:
        flags.append('zero_endpoint')
    if a is None or b is None:
        return 'unknown', tuple(flags)
    if a > b:
        return 'invalid_interval', tuple(flags)
    if 'zero_endpoint' in flags:
        return 'ambiguous_zero', tuple(flags)
    return ('span_compatible' if a <= target <= b else 'outside_recorded_span'), tuple(flags)


def compile_role_evidence(record_id, major, minor, start, end, crosswalk, *, domestic=None, year=200):
    """Deduplicate channels per observation; preserve every unknown source label.

    Crosswalk labels represent source-context evidence only. Never infer a market,
    actor, staff count, population or political authority from these channels.
    """
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError('Nonempty source record ID required')
    channels, unknown = set(), set()
    for level, labels in [('major', major), ('minor', minor)]:
        for label in labels:
            key = str(label).strip().casefold()
            if not key:
                continue
            if key not in crosswalk[level]:
                unknown.add(f'{level}:{key}')
            else:
                channels.update(crosswalk[level][key])
    if str(domestic).strip().casefold() == 'yes':
        channels.add('domestic_observation')
    state, flags = occupation_window(start, end, year)
    return RoleEvidence(record_id, tuple(sorted(channels)), tuple(sorted(unknown)), state, flags)


def association_blocks(record_ids, associations):
    """Conservative validation blocks using exact, namespaced association keys.

    Each association is (record_id, type, namespace, description). Whitespace is
    stripped; identifier case/punctuation is retained. Shared project/event IDs
    can block several places together. Blocks are NOT a settlement crosswalk or
    sufficient spatial independence, even when a block contains only one record.
    """
    ids = set(record_ids)
    if any(not isinstance(i, str) or not i for i in ids):
        raise ValueError('Nonempty string IDs required')
    parent = {i: i for i in ids}
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    keys = {}
    for record, kind, namespace, description in associations:
        if record not in ids:
            raise ValueError('Association refers to missing record')
        key = tuple(str(v).strip() for v in (kind, namespace, description))
        if not key[0] or not key[2]:
            continue
        if key in keys:
            a, b = root(record), root(keys[key])
            parent[max(a, b)] = min(a, b)
        else:
            keys[key] = record
    return {i: root(i) for i in sorted(ids)}
