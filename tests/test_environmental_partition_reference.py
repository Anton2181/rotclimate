"""Manufactured thermal/axis checks; no cached observations or climate run."""
import numpy as np
import pytest
from experiments.v10_forcing_audit import Field
from scripts.audit_environmental_partition import (LEVELS, THRESHOLDS, qualify,
    validate_matched_fields, verify_reference_provenance, withheld_temperature_mae)


def test_legacy_reference_hash_binding_remains_strict_without_duplicate_source_entry():
    row={'url':'https://example.invalid/reference','sha256':'abc','bytes':123}
    verify_reference_provenance({'references':{'field':row},'sources':{}},'field',row)
    verify_reference_provenance({'references':{'field':row},'sources':{'field':'abc'}},'field',row)
    with pytest.raises(ValueError):verify_reference_provenance({'references':{}},'field',row)
    with pytest.raises(ValueError):verify_reference_provenance({'references':{'field':row},'sources':{'field':'changed'}},'field',row)


def test_withheld_pressure_quadrature_has_affine_analytic_solution_and_excludes_anchor():
    p = np.asarray(LEVELS, float)
    observed = np.full((12, 7, 2), 270.)
    error = (2.+p*100e-5)[None, :, None]
    predicted = observed+error
    predicted[:, 0] += 1000.
    np.testing.assert_allclose(withheld_temperature_mae(predicted, observed), 2.+(85000+30000)/2*1e-5)
    with pytest.raises(ValueError): withheld_temperature_mae(predicted, observed, p*100)
    with pytest.raises(ValueError): withheld_temperature_mae(predicted.swapaxes(1, 2), observed.swapaxes(1, 2))


def test_matching_native_axes_rejects_longitude_rotation_and_pressure_unit_change():
    p = np.asarray(LEVELS); latitude = np.array([45., 42.5]); longitude = np.array([230., 232.5])
    field = lambda levels=p, lon=longitude: Field(np.ones((12, len(levels), 2, 2)), levels, latitude, lon, np.arange(12.))
    validate_matched_fields(field(), field())
    with pytest.raises(ValueError): validate_matched_fields(field(), field(lon=longitude[::-1]))
    with pytest.raises(ValueError): validate_matched_fields(field(), field(levels=p*100))


def test_equal_region_qualification_keeps_regional_failure_despite_better_aggregate():
    regions = {}
    for name, thermal in [('a', 1.), ('b', 1.), ('c', 4.)]:
        regions[name] = {'profiles': {'moist': {'thermal_mae_k': 3., 'qsat_shape_mae': .1},
            **{profile: {'thermal_mae_k': thermal, 'qsat_shape_mae': .05}
                for profile in ('environmental_6', 'environmental_6.5')}}}
    reviews = qualify(regions, THRESHOLDS)
    for review in reviews.values():
        assert review['mean_regional']['thermal_mae_k'] == 2.
        assert not review['qualifies']
        assert review['failures'] == ['c: regional thermal MAE protection failed']
