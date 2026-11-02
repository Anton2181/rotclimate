import pytest
from scripts.review_r42_multistart import region_mix_sensitivity


def test_exact_scaled_errors_retain_the_same_ratio_in_every_resample():
    ref = {'a': [1., 2.], 'b': [3., 4.], 'c': [5., 6.]}
    candidate = {n: [x * .9 for x in v] for n, v in ref.items()}
    r = region_mix_sensitivity(ref, candidate, draws=100)
    assert r['interval_95'] == pytest.approx([.9, .9])
    assert r['fraction_below_one'] == 1.
    with pytest.raises(ValueError): region_mix_sensitivity(ref, {'a': [1., 1.]})
    candidate['b'][0] = float('nan')
    with pytest.raises(ValueError): region_mix_sensitivity(ref, candidate)
