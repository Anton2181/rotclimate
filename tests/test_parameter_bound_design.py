import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_bound_probes_preserve_every_other_parameter_and_do_not_disable_the_gate():
    plan=json.loads((ROOT/'calibration/parameter_bounds_20261103/plan.json').read_text())
    read=lambda n:json.loads((ROOT/n).read_text())
    base=read(plan['reference_params'])
    for path in plan['profiles'].values():
        p=read(path)
        changed={k for k in p if p[k]!=base[k]}
        assert changed and changed<={'subsidence_warming_chi0','subsidence_branch_drying'}
        assert 0<p['subsidence_warming_chi0']<1
        assert 0<=p['subsidence_branch_drying']<=2
    assert not set(plan['regions']) & set(read('calibration/sealed_20261103f/regions.json'))


def test_bound_profiles_construct_with_strict_earth_physics():
    from test_earth import _toy_case
    from rotclimate import earth
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    plan=json.loads((ROOT/'calibration/parameter_bounds_20261103/plan.json').read_text())
    case=_toy_case()
    for path in plan['profiles'].values():
        p=Params.from_json(ROOT/path)
        model=ClimateModel(earth.earth_params(p,case),grid=case.grid)
        assert model.p.solver_require_convergence and model.p.moisture_require_convergence
