from copy import deepcopy
import json
from pathlib import Path
import pytest

from scripts.check_column_shear import screening


def cases():
    plan = json.loads(Path('calibration/column_shear_20261026/plan.json').read_text())
    rows = []
    for name in ['reference', *plan['candidates']]:
        for region in plan['regions']:
            rows.append(dict(name=name, region=region, status='passed', legacy_exact=name == 'reference',
                case_identity=region, temperature=dict(monthly_mae_C=2 if name == 'reference' else 1.98),
                rain=dict(loss=1 if name == 'reference' else .9), sst=dict(cells=10, monthly_mae_C=2),
                column_speed=dict(maximum_ms=20, p95_ms=10)))
    return plan, rows


def test_improved_means_cannot_hide_failed_regional_ocean_or_wind_protections():
    plan, rows = cases()
    assert all(row['qualifies'] for row in screening(rows, plan).values())
    for change, reason in [(dict(rain=dict(loss=1.2)), 'combined error'),
        (dict(sst=dict(cells=10, monthly_mae_C=2.021)), 'SST protection'),
        (dict(column_speed=dict(maximum_ms=60.1, p95_ms=10)), 'speed bound')]:
        changed = deepcopy(rows)
        row = next(r for r in changed if r['name'] == 'drag_050' and r['region'] == 'iran_plateau')
        row.update(change)
        review = screening(changed, plan)['drag_050']
        assert not review['qualifies'] and any(reason in failure for failure in review['failures'])


def test_changed_geography_and_sst_cells_are_not_paired():
    plan, rows = cases()
    next(r for r in rows if r['name'] == 'drag_075')['case_identity'] = 'different'
    with pytest.raises(ValueError, match='Unpaired'):
        screening(rows, plan)


def test_failed_solver_and_nonexact_control_cannot_qualify():
    plan, rows = cases()
    next(r for r in rows if r['name'] == 'drag_025')['status'] = 'failed'
    assert not screening(rows, plan)['drag_025']['qualifies']
    next(r for r in rows if r['name'] == 'reference')['legacy_exact'] = False
    with pytest.raises(ValueError, match='exact reference'):
        screening(rows, plan)
