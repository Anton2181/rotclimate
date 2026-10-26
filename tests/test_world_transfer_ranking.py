from copy import deepcopy
from scripts.check_r39_world_transfer import corrected,violation


def metric():
    return dict(zonefit=.2,accuracy=.4,recall=dict(med=.7,cold_wet=.7),
                mediterranean=dict(dry_share=.05,cs_share=.75))


def test_anchor_correction_reproduces_known_native_metrics():
    coarse=metric();native=deepcopy(coarse)
    native['accuracy']=.35;native['recall']['med']=.61;native['zonefit']=.18
    result=corrected(coarse,coarse,native)
    for key in ['zonefit','accuracy']:assert abs(result[key]-native[key])<1e-15
    assert abs(result['recall']['med']-.61)<1e-15


def test_predictions_stay_fractional_without_editing_observed_metrics():
    coarse=metric();native=metric();native['accuracy']=.9
    trial=metric();trial['accuracy']=.8
    assert corrected(trial,coarse,native)['accuracy']==1.
    assert trial['accuracy']==.8


def test_better_objective_cannot_cancel_a_target_violation():
    ref=metric();trial=metric();trial['zonefit']=.3;trial['recall']['med']=.5
    assert violation(trial,ref)>.17
    trial['recall']['med']=.7
    assert violation(trial,ref)==0
