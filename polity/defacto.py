"""De facto control against the de jure claims.

Held land (within HELD_DAYS of a polity's own roads and towns) comes in
patches around the places, with unheld gaps between them. bridge() closes
the gaps in travel time: it adds the land within r days on foot of held land
unless that land is also within r days of land beyond the reach of the
dilation, so gaps narrower than about 2r days are filled and larger unheld
regions (a desert interior, a mountain block) stay open. Fitted on the Roman
empire of AD 150 and tested on its east and on Han China
(scripts/polity_fill_check.py, calibration/polity_20261025/plan_fill.json).
"""
from __future__ import annotations

import numpy as np

from . import control as C

FILL_DAYS = 0.0          # the default gap fill, days (set by the Earth fit)
FILL_CHOICES = (0.0, 0.5, 1.0, 2.0)
# map categories of de jure (painted claims) against de facto (held, bridged)
CATEGORIES = ("held by the claimant", "claimed, unheld", "held by another polity", "held, unclaimed",
              "contested", "neither")


def foot_days(foot_nets, sources, limit=np.inf):
    """Year-round days on foot from the sources (flat cell indices)."""
    if not len(sources):
        return np.full(foot_nets[0].n_cells, np.inf)
    return C.effective_days(np.stack([n.days(sources, limit=limit) for n in foot_nets]))


def bridge(held, land, foot_nets, r, dilated_days=None):
    """held OR (within r days of held AND NOT within r days of land outside that).
    dilated_days: foot_days from the held cells, if already computed."""
    if r <= 0:
        return held.copy()
    shape = held.shape
    if dilated_days is None:
        dilated_days = foot_days(foot_nets, np.flatnonzero(held.ravel()), limit=r + 6).reshape(shape)
    dilated = land & (dilated_days <= r)
    outside = np.flatnonzero((land & ~dilated & ~held).ravel())
    eroded = foot_days(foot_nets, outside, limit=r + 6).reshape(shape) <= r
    return held | (dilated & ~eroded)


def open_regions(held, inside, cell_km, top=5):
    """The largest connected unheld land regions inside a polygon, km2."""
    from scipy import ndimage as ndi
    lab, n = ndi.label(inside & ~held)
    if not n:
        return []
    sizes = np.bincount(lab.ravel())[1:] * cell_km ** 2
    return [float(s) for s in np.sort(sizes)[::-1][:top]]


def categories(claim, held_by, contested):
    """Per cell index into CATEGORIES. claim: de jure polity index (-1 none);
    held_by: de facto polity index (-1 none); contested: bool."""
    cat = np.full(claim.shape, 5, np.int8)
    cat[(held_by >= 0) & (claim == held_by)] = 0
    cat[(claim >= 0) & (held_by < 0)] = 1
    cat[(claim >= 0) & (held_by >= 0) & (claim != held_by)] = 2
    cat[(claim < 0) & (held_by >= 0)] = 3
    cat[contested & (held_by >= 0)] = 4
    return cat


def map_fields(r, choices=FILL_CHOICES):
    """De facto control on the map for each gap fill in `choices` (days), from
    polity.fields.compute's result: the held land (within HELD_DAYS of the
    nearest polity's own network) bridged, each cell given to the polity whose
    network is nearest, contested where a rival is within CONTESTED_DAYS."""
    from . import network as N
    from .fields import CONTESTED_DAYS, HELD_DAYS
    land, f = r["land"], r["fields"]
    best, best_days, second_days = f["polity_best"], f["polity_best_days"], f["polity_second_days"]
    held = land & (best_days <= HELD_DAYS)
    foot = [N.month_network(r["world"], r["statics"], r["climate"], m, boats=False) for m in range(12)]
    dil = foot_days(foot, np.flatnonzero(held.ravel()), limit=max(choices) + 6).reshape(land.shape)
    out = {}
    for c in choices:
        b = bridge(held, land, foot, c, dil)
        held_by = np.where(b, best, -1)
        with np.errstate(invalid="ignore"):
            contested = b & (second_days - best_days <= CONTESTED_DAYS)
        out[c] = dict(bridged=b, held_by=held_by, contested=contested,
                      category=categories(r["claim"], held_by, contested))
    return out


def polity_table(r, d):
    """People (central occupation scenario) and area by polity, de jure against de facto."""
    km2 = r["cell_km"] ** 2
    ppl = np.where(r["land"], r["density"], 0.0) * km2
    claim, held_by, contested = r["claim"], d["held_by"], d["contested"]
    rows = []
    for k, name in enumerate(r["polity_names"]):
        c, h = claim == k, held_by == k
        rows.append(dict(
            polity=name, claimed_km2=float(c.sum() * km2), held_km2=float(h.sum() * km2),
            claimed_people=float(ppl[c].sum()), held_people=float(ppl[h].sum()),
            held_in_claim_people=float(ppl[c & h].sum()), claimed_unheld_people=float(ppl[c & (held_by < 0)].sum()),
            claimed_held_by_others_people=float(ppl[c & (held_by >= 0) & ~h].sum()),
            held_outside_claim_people=float(ppl[h & ~c].sum()), contested_people=float(ppl[h & contested].sum()),
            mobile=bool(r["mobile"].get(name, False))))
    total = dict(people=float(ppl.sum()), unclaimed_unheld_people=float(ppl[(claim < 0) & (held_by < 0)].sum()),
                 unclaimed_unheld_km2=float(((claim < 0) & (held_by < 0) & r["land"]).sum() * km2))
    return rows, total
