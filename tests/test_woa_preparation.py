from pathlib import Path
import gzip
import io
import numpy as np
import pytest

from scripts.prepare_woa18 import NAMES,check,raw_sources,fetch_missing


def make_cache(tmp_path):
    folder=tmp_path/'raw'
    folder.mkdir()
    for name in NAMES:
        (folder/name).write_bytes(name.encode())
    sources=raw_sources(folder)
    values=dict(sst=np.full((12,180,360),15,np.float32),lat=np.arange(180)-89.5,
                lon=np.arange(360)-179.5,sources=np.array(sorted(sources.items())))
    cache=tmp_path/'sst.npz'
    np.savez_compressed(cache,**values)
    return folder,cache,values


def test_complete_reference_is_verified_and_changed_raw_file_is_rejected(tmp_path):
    folder,cache,_=make_cache(tmp_path)
    assert check(cache,raw_sources(folder))['status']=='passed'
    (folder/NAMES[5]).write_bytes(b'changed observation archive')
    with pytest.raises(ValueError,match='checksums differ'):
        check(cache,raw_sources(folder))


def test_missing_month_cannot_silently_become_a_seasonal_reference(tmp_path):
    folder,_,_=make_cache(tmp_path)
    (folder/NAMES[2]).unlink()
    with pytest.raises(ValueError,match='Incomplete monthly'):
        raw_sources(folder)


def test_download_is_published_only_after_full_gzip_validation(tmp_path,monkeypatch):
    monkeypatch.setattr('scripts.prepare_woa18.urllib.request.urlopen',
                        lambda *a,**k:io.BytesIO(gzip.compress(b'valid monthly source')))
    fetch_missing(tmp_path,NAMES[0])
    assert gzip.decompress((tmp_path/NAMES[0]).read_bytes())==b'valid monthly source'
    monkeypatch.setattr('scripts.prepare_woa18.urllib.request.urlopen',
                        lambda *a,**k:io.BytesIO(b'<html>upstream error</html>'))
    with pytest.raises(gzip.BadGzipFile):fetch_missing(tmp_path,NAMES[1])
    assert not (tmp_path/NAMES[1]).exists()
    assert not list(tmp_path.glob('*.download'))


@pytest.mark.parametrize('field', ['temperature','coordinates','provenance'])
def test_numerical_array_shape_does_not_excuse_wrong_reference(tmp_path,field):
    folder,cache,values=make_cache(tmp_path)
    if field=='temperature':
        values['sst'][5]=np.nan
    elif field=='coordinates':
        values['lon']=values['lon']+1
    else:
        values['sources'][2]=values['sources'][1]
    np.savez_compressed(cache,**values)
    with pytest.raises(ValueError):
        check(cache,raw_sources(folder))
