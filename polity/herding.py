"""Herding share of food (calibration/herders_20261120/plan_v2.json, adopted 20 Nov 2026; blind Spearman 0.42 vs -0.06 for the
grazing-capacity share): H = b + a x clip((hi - LGP) / (hi - lo), 0, 1), LGP the growing-season days, averaged over ~27 km.
Used for the per-polity herding statistics; the same rule draws the 'Herders and farmers' layer (scripts/herders_layer.py)."""
import json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

SPEC = json.loads((Path(__file__).resolve().parents[1] / 'output/herders_20261120/v2_dev.json').read_text())['chosen']


def share(lgp, land, cell_km):
    m = np.clip((SPEC['hi'] - np.nan_to_num(lgp)) / (SPEC['hi'] - SPEC['lo']), 0, 1)
    k = max(1, int(round(27.0 / cell_km))) | 1
    w = np.maximum(ndi.uniform_filter(land.astype(float), k, mode='nearest'), 1e-9)
    m = ndi.uniform_filter(np.where(land, m, 0.0), k, mode='nearest') / w
    return np.where(land, np.clip(SPEC['b'] + SPEC['a'] * m, 0, 1), 0.0)
