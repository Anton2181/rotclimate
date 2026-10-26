from scripts.check_surface_momentum import branch_failures
from rotclimate.config import Params


def test_later_gates_cannot_hide_fast_return_or_missing_mass_tracer_certificate():
    p=Params().replace(moisture_two_layer=True,moisture_mass_tracer=True)
    row=dict(numerics=dict(two_layer_transport=dict(max_scaled_dry_mass_divergence=1e-14,
        maximum_branch_speed_ms=20,p95_branch_speed_ms=10),mass_tracer_transport=dict(mass_aware_advection_diffusion_storms=True)))
    assert branch_failures({'region':row},p)==[]
    row['numerics']['two_layer_transport']['maximum_branch_speed_ms']=61
    assert branch_failures({'region':row},p)
    row['numerics']['two_layer_transport']['maximum_branch_speed_ms']=20
    del row['numerics']['mass_tracer_transport']
    assert branch_failures({'region':row},p)
    assert branch_failures({'legacy':dict(numerics={})},Params())==[]


def test_every_later_gate_requires_active_pressure_profile_certificate():
    p=Params(column_saturation_scheme='pressure-moist')
    row=dict(numerics={})
    assert branch_failures({'region':row},p)
    row['numerics']['column_thermodynamics']=dict(scheme='pressure-lapse',steps=[{}])
    assert branch_failures({'region':row},p)
    row['numerics']['column_thermodynamics']=dict(scheme='pressure-moist',steps=[dict(minimum_column_capacity_mm=1.)])
    assert branch_failures({'region':row},p)==[]
