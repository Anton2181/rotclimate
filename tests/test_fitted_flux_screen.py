import json
from pathlib import Path

from scripts.screen_fitted_flux import publication_files

ROOT=Path(__file__).resolve().parents[1]


def test_screen_changes_only_the_declared_vapor_face_stencil():
    plan=json.loads((ROOT/'calibration/fitted_flux_20261103/plan.json').read_text())
    read=lambda path:json.loads((ROOT/path).read_text())
    ref=read(plan['reference']);up=read(plan['profiles']['upwind_flux']);fit=read(plan['profiles']['fitted_flux'])
    assert {k for k in ref if ref[k]!=up[k]}=={'moisture_transport_form','flux_convergence','eddy_moisture_scheme'}
    assert {k for k in up if up[k]!=fit[k]}=={'moisture_flux_scheme'}
    assert fit['moisture_flux_scheme']=='exponential'
    assert up['moisture_diffusion']==fit['moisture_diffusion']==60000
    assert ref['wind_source']==fit['wind_source']=='model'
    assert ref['sst_source']==fit['sst_source']=='model'
    assert not set(plan['regions']) & set(read('calibration/sealed_20261103f/regions.json'))


def test_screen_publication_excludes_private_model_and_transient_markers(tmp_path):
    (tmp_path/'model/data').mkdir(parents=True)
    (tmp_path/'model/data/archive.json').write_text('{}')
    (tmp_path/'status.json').write_text('{}')
    (tmp_path/'push.log').write_text('')
    (tmp_path/'result.json').write_text('{}')
    assert publication_files(tmp_path)==[tmp_path/'result.json']
