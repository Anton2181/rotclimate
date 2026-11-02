import pytest
from scripts.audit_earth_region_separation import audit, bounds, overlap


def test_longitude_wrapping_detects_overlap_across_the_dateline():
    assert overlap([177, 181, 0, 4], [-181, -177, 1, 3])
    assert not overlap([177, 181, 0, 4], [-175, -171, 1, 3])
    assert not overlap([177, 181, 0, 4], [-181, -177, 5, 6])


def test_margin_protects_against_rounded_scoring_cells_and_duplicate_names():
    a = dict(lat0=0., lon0=0., width_km=100., height_km=100.)
    b = dict(a, lon0=1.2)
    assert audit({'new': b}, {'old': a}, margin_km=0)['passes']
    assert not audit({'new': b}, {'old': a}, margin_km=56)['passes']
    assert not audit({'old': dict(b, lon0=20)}, {'old': a})['passes']
    with pytest.raises(ValueError): bounds(dict(a, lat0=float('nan')))
