"""Reject cross-fold panel leakage, including place-label aliases."""
from collections import defaultdict


def panel_leakage(cases):
    groups=defaultdict(list)
    for c in cases:groups[c['household_id']].append(c)
    crossing={k:v for k,v in groups.items() if len({c['split'] for c in v})>1}
    return crossing


def require_independent_panels(cases):
    crossing=panel_leakage(cases)
    if crossing:raise ValueError(f'Invalid geographic split: {len(crossing)} households occur in multiple folds. Canonicalize place identities and preserve panels before scoring; a changed split needs a new declared protocol.')
