"""Malaria suitability adopted 20 Nov 2026 (reports/MALARIA_GENETICS_20261120.md; calibration/malaria_genetics_20261120/plan.json):
the share of months whose Mordecai et al. (2013) relative thermal suitability reaches the season threshold, with no rain gate
(blind Spearman vs the sickle-cell footprint 0.55 against 0.11 for the rain-gated annual mean). The health penalty is rescaled so
the map's mean malaria burden is unchanged (data/malaria_model.json): the 0.35 maximum was never calibrated and the population
totals were set with the old field."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; MODEL = ROOT / 'data/malaria_model.json'


def model(require_active=True):
    m = json.loads(MODEL.read_text()) if MODEL.exists() else None
    return m if m and (m.get('active_in_export') or not require_active) else None


def malaria_fields(temperature):
    from harvest.models import malaria_thermal
    spec = model(require_active=False); t = np.asarray(temperature)
    if t.shape[0] != 12:
        raise ValueError('Malaria needs twelve months')
    ok = malaria_thermal(t) >= spec['season_threshold']
    return dict(malaria=ok.mean(0), malaria_months=ok.sum(0))


def penalty_input(malaria):
    """The value to hand settlement_fields (whose health is 1 - 0.35 x input) so health = 1 - penalty x malaria."""
    from harvest.models import specification
    return np.asarray(malaria) * model(require_active=False)['maximum_malaria_penalty'] / specification()['maximum_malaria_penalty']
