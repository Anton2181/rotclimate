import pytest
from scripts.check_constrained_blend import proposals


def archive():
    return [dict(n=0,S=1.,T=2.,P=.5,groups=dict(a=1.,b=1.),knobs=dict(q=0.,solar_flux=1.)),
            dict(n=1,S=.99,T=1.98,P=.495,groups=dict(a=.96,b=1.02),knobs=dict(q=0.,solar_flux=1.)),
            dict(n=2,S=.98,T=1.96,P=.49,groups=dict(a=1.02,b=.94),knobs=dict(q=1.,solar_flux=2.))]


def test_complementary_responses_produce_bounded_shared_parameters_only():
    result=proposals(archive(),[['q',0.,1.]],[.995],[.75,1.])
    assert len(result['proposals'])==2
    smaller,full=result['proposals']
    assert set(full['knobs'])=={'q'}
    assert 0<=full['knobs']['q']<=1
    assert smaller['knobs']['q']==pytest.approx(.75*full['knobs']['q'])
    for point in result['proposals']:
        assert sum(x['weight'] for x in point['support'])==pytest.approx(1.)
        assert point['predicted_S']<.995


def test_infeasible_group_target_creates_no_fallback_candidate():
    result=proposals(archive(),[['q',0.,1.]],[.90],[1.])
    assert result['proposals']==[]
    assert result['linear_screens'][0]['feasible'] is False


def test_interpolation_does_not_present_predicted_losses_as_measured_climate():
    result=proposals(archive(),[['q',0.,1.]],[.995],[.75])
    assert 'observed climate' in result['note']
    assert 'actual_S' not in result['proposals'][0]
