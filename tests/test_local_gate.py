import copy

import pytest

from scripts.gate_local import evaluate
from scripts.local_benchmark_protocol import identity


def inputs():
    policy = dict(groups=dict(first=['a'], second=['b']))
    protocol = dict(regions=['a','b'], region_specs=dict(a={},b={}), cell_km=56,
        sources={'model':'same source', 'observations':'same observations'},
        params=dict(steps_per_year=25, solver_rtol=1e-6, moisture_residual_tol=.01,
                    t_require_convergence=True, moisture_require_convergence=True, solver_require_convergence=True))
    run_id = identity(protocol)
    ref = dict(complete=True, identity=run_id, cell_km=56, regions={name:dict(region=name,
        status='passed', identity=run_id, cells=100, case_identity='grid-'+name,
        numerics=dict(all_checks_passed=True), temperature=dict(monthly_mae_C=2), rain=dict(loss=.5))
        for name in ['a','b']})
    candidate = copy.deepcopy(ref)
    for row in candidate['regions'].values():
        row['temperature']['monthly_mae_C'] *= .98
        row['rain']['loss'] *= .98
    return ref, candidate, protocol, copy.deepcopy(protocol), policy


def test_gate_uses_regional_records_and_requires_group_protection():
    b,c,bp,cp,p = inputs()
    c['all'] = dict(T_monthly_mae=0, P_loss=0)  # An incorrect aggregate is never trusted.
    assert evaluate(b,c,bp,cp,p)['score'] == pytest.approx(.98)
    c['regions']['a']['temperature']['monthly_mae_C'] = 2.1
    c['regions']['b']['temperature']['monthly_mae_C'] = 1.5
    review = evaluate(b,c,bp,cp,p)
    assert review['score'] < .995
    assert not review['passes_development_gate']
    assert 'first: group score worsened' in review['failures']


def test_gate_rejects_missing_regions_even_if_the_summary_looks_better():
    b,c,bp,cp,p = inputs();del c['regions']['b']
    with pytest.raises(ValueError, match='exact policy regions'): evaluate(b,c,bp,cp,p)


def test_numerical_failures_and_different_observation_masks_are_not_admissible():
    b,c,bp,cp,p = inputs();c['regions']['a']['numerics']['all_checks_passed'] = False
    with pytest.raises(ValueError, match='Unverified numerical'): evaluate(b,c,bp,cp,p)
    c['regions']['a']['numerics']['all_checks_passed'] = True
    c['regions']['a']['case_identity'] = 'different observations'
    with pytest.raises(ValueError, match='geography or observations differ'): evaluate(b,c,bp,cp,p)


def test_changed_physics_source_cannot_be_hidden_by_an_updated_manifest_id():
    b,c,bp,cp,p = inputs();cp['sources']['model'] = 'changed model'
    c['identity'] = identity(cp)
    for row in c['regions'].values(): row['identity'] = c['identity']
    with pytest.raises(ValueError, match='sources or observations changed'): evaluate(b,c,bp,cp,p)


def test_coarser_temporal_sampling_is_not_paired_evidence():
    b,c,bp,cp,p = inputs();cp['params']['steps_per_year'] = 13
    c['identity'] = identity(cp)
    for row in c['regions'].values(): row['identity'] = c['identity']
    with pytest.raises(ValueError, match='Numerical criteria differ'): evaluate(b,c,bp,cp,p)


def test_a_no_change_control_cannot_pass_the_adoption_gate():
    b,_,bp,cp,p = inputs()
    review = evaluate(b,b,bp,cp,p)
    assert review['score'] == 1
    assert not review['passes_development_gate']
