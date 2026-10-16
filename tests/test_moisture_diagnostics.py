from dataclasses import asdict
import json

from rotclimate.config import Params
from scripts.diagnose_moisture import completed_comparisons


def test_completed_transport_comparison_survives_running_only_the_other_case(tmp_path):
    p = Params(moisture_residual_tol=.01, moisture_require_convergence=True)
    detail = dict(params=asdict(p), accuracy=.43, zones={
        'med': {'correct': .18, 'koppen_share': {'BSh': .2, 'BSk': .03, 'Csa': .21, 'Cfa': .56}}},
        solver={'unconverged_solves': 0},
        temperature_convergence={'unconverged_steps': 0, 'final_update_max_c': [.04]},
        moisture_convergence={'enabled': True, 'unconverged_steps': 0},
        moisture_transport={'zones': {}})
    (tmp_path/'current.json').write_text(json.dumps(detail))
    (tmp_path/'current_fields.npz').touch()
    (tmp_path/'current_transport.npz').touch()
    rows=completed_comparisons(tmp_path, {'current': p, 'focused': p.replace(eddy_rate=1.)})
    assert list(rows)==['current']
    assert abs(rows['current']['mediterranean']['dry_share']-.23)<1e-12
    assert rows['current']['convergence']['moisture_convergence_checked']
    assert not completed_comparisons(tmp_path, {'current': p.replace(moisture_residual_tol=.02)})
