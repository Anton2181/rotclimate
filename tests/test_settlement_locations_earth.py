"""Check validation semantics and source recovery, without claiming Earth skill."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import settlement_locations_earth as earth
import recover_settlement_sources as recovery


def grid():
    shape=(40,60)
    return dict(land=np.ones(shape,bool),allowed=np.ones(shape,bool),cell_km=9.,
                real=np.ravel_multi_index(([5,5,25],[5,6,40]),shape))


def test_proximity_does_not_claim_distinct_site_recovery():
    x=grid()
    result=earth.metrics(x,[(5,5),(25,40)])
    assert result['recall']==result['precision']==result['F1']==1.
    assert result['unique_matches']==2
    assert result['unique_F1']==.8


def test_exact_locations_have_zero_spacing_distance():
    result=earth.metrics(grid(),[(5,5),(5,6),(25,40)])
    assert result['M3']==0.
    assert result['unique_F1']==1.
    assert result['M1']==pytest.approx(1.)


def test_outside_allowed_observations_are_not_targets():
    x=grid();x['allowed'][5,6]=False
    result=earth.metrics(x,[(5,5),(25,40)])
    assert result['n_real']==result['n_model']==2
    assert result['unique_F1']==1.


def test_prefix_diagnostic_does_not_replace_full_count_scoring():
    result=earth.metrics(grid(),[(5,5),(5,6),(25,40),(38,59)])
    assert result['n_model']==4 and result['F1']<1.
    assert result['historical_best_prefix']['n_model']==3
    assert result['historical_best_prefix']['F1']==1.


def test_remote_zip_range_checks_server_response(monkeypatch):
    class Response:
        status=206
        headers={'Content-Range':'bytes 8-11/12'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'ijkl'
    def get(request,timeout):
        assert request.get_header('Range')=='bytes=8-11'
        return Response()
    monkeypatch.setattr(recovery.urllib.request,'urlopen',get)
    f=recovery.RangeReader('https://example.org/archive.zip',12)
    assert f.seek(-4,2)==8 and f.read()==b'ijkl' and f.tell()==12
    assert f.read()==b''
    Response.status=200
    f.seek(8)
    with pytest.raises(ValueError,match='byte range'):f.read()


def test_remote_zip_short_reads_fail(monkeypatch):
    class Response:
        status=206
        headers={'Content-Range':'bytes 0-3/4'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'abc'
    monkeypatch.setattr(recovery.urllib.request,'urlopen',lambda *a,**kw:Response())
    with pytest.raises(ValueError,match='Truncated'):
        recovery.RangeReader('https://example.org/archive.zip',4).read()
