import numpy as np
from rotclimate import biomes


def test_typical_climates_units_and_ocean_mask():
    # Interior points from the published temperature/precipitation envelopes.
    t = np.array([27, 27, 27, 10, 10, 2, -10, 10, 18, 45, 27.])
    p = np.array([3000, 1400, 100, 2200, 1100, 900, 200, 300, 650, 1000, 3000.])
    land = np.ones(t.shape, bool); land[-1] = False
    assert biomes.classify(t, p, land).tolist() == [4, 1, 2, 3, 9, 7, 6, 8, 5, 0, 255]


def test_edges_are_deterministic_and_invalid_inputs_not_extrapolated():
    for vertices in biomes.polygons().values():
        got = biomes.classify(vertices[:,0], vertices[:,1])
        assert np.all((got >= 1) & (got <= 9))
    assert biomes.classify([np.nan, 100, 20], [100, 100, -1]).tolist() == [0, 0, 0]
    assert int(biomes.classify(27., 3000.)) == 4


def test_land_shares_include_outside_but_exclude_ocean():
    classes = np.array([4, 4, 0, 255], np.uint8)
    legend = biomes.legend(classes, classes != 255)
    assert np.isclose(sum(r['share'] for r in legend), 1)
    assert legend[4]['share'] == 2/3 and legend[0]['share'] == 1/3
