import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_single_fixed_candidate_changes_only_the_existing_loss_rate():
    plan=json.loads((ROOT/'calibration/dry_branch_validation_20261103/plan.json').read_text())
    read=lambda n:json.loads((ROOT/n).read_text())
    reference=read(plan['reference'])
    assert list(plan['candidates'])==['dry_branch_040']
    candidate=read(plan['candidates']['dry_branch_040'])
    assert {k for k in reference if reference[k]!=candidate[k]}=={'subsidence_branch_drying'}
    assert candidate['subsidence_branch_drying']==.4
    assert set(plan['regions'])==set(read(plan['region_specs']))
    assert len(plan['regions'])==61 and len(plan['historical49'])==49
    assert not set(plan['regions']) & set(read(plan['holdout']))
    assert plan['model_commit']==read('calibration/fitted_flux_20261103/plan.json')['model_commit']
