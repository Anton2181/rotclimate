from copy import deepcopy
from scripts.check_r39_world_robust import training_failures


def setup():
    metric=dict(zonefit=.2,accuracy=.4,recall=dict(tree=.1),mediterranean=dict(dry_share=.05,cs_share=.8))
    batches=dict(initial=deepcopy(metric),extra=deepcopy(metric))
    return metric,batches


def test_five_layout_gain_cannot_hide_a_known_batch_regression():
    ref,batches=setup();combined=deepcopy(ref);combined['zonefit']=.3
    batches['extra']['zonefit']=.19
    predicted=deepcopy(ref);predicted['zonefit']+=.0011
    assert training_failures(batches,combined,dict(initial=ref,extra=ref),ref,predicted,ref)==['extra: training batch zonefit worsened']


def test_native_region_loss_cannot_be_hidden_by_training_gain():
    ref,batches=setup();predicted=deepcopy(ref);predicted['zonefit']=.3;predicted['recall']['tree']=.01
    assert 'Predicted native protections failed' in training_failures(batches,ref,batches,ref,predicted,ref)


def test_all_training_protections_must_pass():
    ref,batches=setup();predicted=deepcopy(ref);predicted['zonefit']+=.0011
    assert training_failures(batches,ref,batches,ref,predicted,ref)==[]
