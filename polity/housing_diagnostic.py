"""Blocked diagnostics of sampled property density, not census prediction.

The unit is a city observation. Household scenarios are not extra observations;
unknown sample phases and representativeness remain separate measurement gates.
"""
import numpy as np


MODELS = ('constant', 'area', 'area_coverage')


def design(rows, model):
    if model not in MODELS:
        raise ValueError('Unknown housing diagnostic model')
    areas = np.array([[r['site_area_ha'], r['sample_area_ha']] for r in rows], float)
    if areas.shape != (len(rows), 2) or not len(rows):
        raise ValueError('Nonempty housing observations required')
    if not np.isfinite(areas).all() or np.any(areas <= 0) or np.any(areas[:, 1] > areas[:, 0]):
        raise ValueError('Finite positive sample and site areas required')
    columns = [np.ones(len(rows))]
    if model != 'constant':
        columns.append(np.log(areas[:, 0]))
    if model == 'area_coverage':
        columns.append(np.log(areas[:, 1] / areas[:, 0]))
    return np.column_stack(columns)


def fit_predict(training, held_out, model, *, household=1.):
    """Fit only training targets and return held-out log-density predictions.

    A common household size merely changes the log-density unit. No rounding,
    weighting by discovered buildings, range clipping or missing-area filling.
    Held-out targets are deliberately never read here.
    """
    if isinstance(household, bool) or not np.isfinite(household) or household <= 0:
        raise ValueError('Finite positive household scenario required')
    x, target_x = design(training, model), design(held_out, model)
    counts = np.array([r['properties'] for r in training], float)
    if not np.isfinite(counts).all() or np.any(counts <= 0) or np.any(counts != np.floor(counts)):
        raise ValueError('Positive integer encountered property counts required')
    # Sum logarithms rather than form ratios/products that can overflow.
    y = np.log(counts) - np.log([r['sample_area_ha'] for r in training]) + np.log(household)
    coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank != x.shape[1]:
        raise ValueError('Rank-deficient housing diagnostic design')
    prediction = target_x @ coefficients
    if not np.isfinite(coefficients).all() or not np.isfinite(prediction).all():
        raise ValueError('Nonfinite housing diagnostic fit')
    return coefficients, prediction


def province_folds(rows, *, minimum_training=10):
    """Keep all same-province observations together; never use row-wise folds."""
    groups = sorted({r['province'] for r in rows})
    if len(groups) < 3:
        raise ValueError('Each fold needs at least two training provinces')
    folds = []
    for group in groups:
        train = [i for i, r in enumerate(rows) if r['province'] != group]
        test = [i for i, r in enumerate(rows) if r['province'] == group]
        if len(train) < minimum_training:
            raise ValueError('Fewer than ten training cities in held-province fold: ' + group)
        folds.append((group, train, test))
    return folds
