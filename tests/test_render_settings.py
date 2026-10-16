"""Rendering must be able to reproduce a verified numerical configuration."""
from argparse import Namespace
from dataclasses import asdict

import numpy as np

from rotclimate.__main__ import render_params
from rotclimate.config import Params
from rotclimate.geography import TARGET_CLASSES
from rotclimate.koppen import CODES
from rotclimate.score import best_zone, display_zones


def test_saved_settings_survive_render_setup():
    p = Params.from_json('calibration/round19_earthlike_strict.json')
    a = Namespace(saved_numerics=True, downsample=None, steps=None, picard=None)
    assert asdict(render_params(p, a)) == asdict(p)
    assert p.solver_require_convergence and p.solver_rtol == 1e-6
    assert (p.downsample, p.steps_per_year, p.picard_iters) == (4, 25, 2)


def test_explicit_render_override_preserves_solver_settings():
    p = Params(solver_rtol=1e-6, solver_require_convergence=True)
    a = Namespace(saved_numerics=True, downsample=4, steps=73, picard=6)
    q = render_params(p, a)
    assert (q.downsample, q.steps_per_year, q.picard_iters) == (4, 73, 6)
    assert q.solver_rtol == 1e-6 and q.solver_require_convergence


def test_legacy_render_defaults_are_unchanged():
    a = Namespace(saved_numerics=False, downsample=None, steps=None, picard=None)
    p = render_params(Params(downsample=16, steps_per_year=25, picard_iters=2), a)
    assert (p.downsample, p.steps_per_year, p.picard_iters) == (4, 73, 3)


def test_verified_moisture_profile_is_preserved_even_without_the_saved_flag():
    p=Params.from_json('calibration/round20_retrograde_seasonal_verified.json')
    a=Namespace(saved_numerics=False,downsample=None,steps=None,picard=None)
    assert asdict(render_params(p,a))==asdict(p)


def test_display_policy_difference_does_not_change_strict_benchmark():
    mem = {key: np.zeros((1, 3)) for _, key, _, _ in TARGET_CLASSES}
    mem['tree'][:] = 0.85
    mem['warm_wet'][:] = 0.8
    kop = np.full((1, 3), CODES.index('Cfa'))
    land = np.array([[True, True, False]])
    ix = dict(Thot=np.array([[25., 10., 25.]]), aridity=np.full((1, 3), 3.))
    strict = best_zone(mem, koppen=kop)
    display = display_zones(mem, land, ix=ix, elev=np.zeros((1, 3)), koppen=kop)
    assert strict.tolist() == [[6, 6, 6]]
    assert display.tolist() == [[3, 8, -1]]
