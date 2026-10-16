import io
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from PIL import Image,TiffImagePlugin
import pytest
from scipy.io import netcdf_file

from rotclimate_v10.core import Config,Domain,State
from rotclimate_v10.earth import EarthCase,SOURCES,sample_tiff,read_sst,save_case,load_case,fetch_raw
from rotclimate_v10.integrate import YearResult
from scripts import run_v10_pilot as pilot


def make_case():
    mask = np.ones((3,3),bool)
    d = Domain('fake',mask,np.zeros((3,3)),np.full((3,3),40.),np.full((12,3,3),15.),60000.,60000.)
    return EarthCase(d,np.zeros((3,3)),np.full((12,3,3),20.),mask,np.full((3,3),100.),np.zeros((3,3),bool))


def test_geotiff_tie_point_centres_and_nodata(tmp_path):
    path = tmp_path/'fake.tif'
    a = np.array([[10,-30,-9999],[40,50,60]],dtype=np.float32)
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[33550] = (2.,3.,0.);tags[33922] = (0.,0.,0.,-10.,50.,0.)
    tags[42113] = '-9999';tags[34735] = (1,1,0,1,1025,0,1,1)
    Image.fromarray(a).save(path,tiffinfo=tags)
    with Image.open(path) as im:
        lon = np.array([[-9.,-7.,-5.,-11.]])
        lat = np.full_like(lon,48.5)
        result = sample_tiff(im,lon,lat)
    np.testing.assert_allclose(result[:,:2],[[10,-30]])
    assert np.isnan(result[:,2:]).all()


def test_packed_sst_scaling_fill_and_longitude_wrap(tmp_path):
    path = tmp_path/'sst.nc'
    with netcdf_file(path,'w') as f:
        for name,size in (('time',12),('lat',2),('lon',3)):f.createDimension(name,size)
        f.createVariable('lat','f',('lat',))[:] = [40,30]
        f.createVariable('lon','f',('lon',))[:] = [0,120,240]
        v = f.createVariable('sst','h',('time','lat','lon'))
        a = np.full((12,2,3),100,dtype=np.int16);a[:,:,2] = 200;a[:,0,1] = -32767
        v[:] = a;v.missing_value = np.int16(-32767);v.scale_factor = np.float32(.1);v.add_offset = np.float32(5);v.units = b'degC'
    result = read_sst(path,np.array([[-120.,0.]]),np.array([[40.,30.]]))
    np.testing.assert_allclose(result[:,0,0],25,rtol=1e-7)
    np.testing.assert_allclose(result[:,0,1],15,rtol=1e-7)


def test_prepared_case_roundtrip(tmp_path):
    case = make_case();path = tmp_path/'case.npz';save_case(path,case)
    loaded = load_case(path,'fake')
    np.testing.assert_array_equal(case.observed_rain_mm,loaded.observed_rain_mm)
    np.testing.assert_array_equal(case.domain.temperature_c,loaded.domain.temperature_c)


def fake_integrator(counter,fail_at=None):
    def run(d,c,state,storms,progress):
        counter.append(1)
        if fail_at is not None and len(counter)==fail_at:raise RuntimeError('manufactured interruption')
        b = dict(annual_water_error_mm=0.,max_step_water_error_mm=0.,max_air_continuity_kg_m2_s=0.,min_store_mm=0.)
        return YearResult(state,np.full((12,)+d.land.shape,10.),b)
    return run


def test_resume_after_completed_year_only(tmp_path):
    case = make_case();calls = []
    with pytest.raises(RuntimeError,match='interruption'):
        pilot.run_case(case,Config(),tmp_path,True,integrator=fake_integrator(calls,2))
    assert (tmp_path/'year1.json').is_file() and not (tmp_path/'year2.json').exists()
    calls = []
    summary,_ = pilot.run_case(case,Config(),tmp_path,True,integrator=fake_integrator(calls))
    assert len(calls)==2 and summary['settling']['passed']
    calls = []
    pilot.run_case(case,Config(),tmp_path,True,integrator=fake_integrator(calls))
    assert calls==[]


def test_corrupted_checkpoint_is_not_reused(tmp_path):
    case = make_case();pilot.run_case(case,Config(),tmp_path,True,integrator=fake_integrator([]))
    (tmp_path/'year1.npz').write_bytes(b'broken')
    with pytest.raises(ValueError,match='checkpoint'):
        pilot.read_year(tmp_path,1,(3,3))


def test_failed_water_budget_is_not_scored(tmp_path):
    case = make_case();s = State(*(np.ones((3,3)) for _ in range(3)))
    r = YearResult(s,np.ones((12,3,3)),dict(annual_water_error_mm=1.,max_step_water_error_mm=0.,
                                         max_air_continuity_kg_m2_s=0.,min_store_mm=0.))
    with pytest.raises(ValueError,match='budget'):
        pilot.write_year(tmp_path,1,r,0.)
    assert not (tmp_path/'year1.json').exists()


def test_default_is_read_only_and_never_downloads_or_runs(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,'prepare_inputs',lambda *a:pytest.fail('unexpected preparation'))
    assert pilot.main(['--out',str(tmp_path/'out'),'--cache',str(tmp_path/'cache')])==0
    assert list(tmp_path.iterdir())==[]


def test_no_run_without_inputs(tmp_path):
    assert pilot.main(['--run','--out',str(tmp_path/'out'),'--cache',str(tmp_path/'cache')])==2
    assert not (tmp_path/'out').exists()


def test_changed_manifest_blocks_all_integrations(tmp_path,monkeypatch):
    path = tmp_path/'fake.npz';save_case(path,make_case())
    monkeypatch.setattr(pilot,'prepare_inputs',lambda *a:{'fake':path})
    monkeypatch.setattr(pilot,'run_case',lambda *a,**kw:pytest.fail('unexpected simulation'))
    out = tmp_path/'out';out.mkdir();(out/'manifest.json').write_text('{}')
    assert pilot.main(['--run','--out',str(out)])==2


def test_complete_runner_and_plot_output_with_fake_integrations(tmp_path,monkeypatch):
    paths = {}
    for name in ('california','iberia'):
        case = make_case();case.domain.name = name
        path = tmp_path/f'{name}.npz';save_case(path,case);paths[name] = path
    monkeypatch.setattr(pilot,'prepare_inputs',lambda *a:paths)
    real_run_case = pilot.run_case;calls = []
    monkeypatch.setattr(pilot,'run_case',lambda *a,**kw:real_run_case(*a,**kw,integrator=fake_integrator(calls)))
    out = tmp_path/'out'
    assert pilot.main(['--run','--out',str(out)])==0
    assert len(calls)==12
    report = json.loads((out/'summary.json').read_text())
    assert len(report['cases'])==4 and report['failures']==[] and report['atlas_updated'] is False
    assert len(list(out.glob('*_rainfall.png')))==2
    assert pilot.main(['--run','--out',str(out)])==0
    assert len(calls)==12  # completed cases perform no repeated integration


def test_download_cleans_partial_file_after_failure(tmp_path,monkeypatch):
    class Broken(io.BytesIO):
        def read(self,*a):raise OSError('manufactured dropped connection')
    monkeypatch.setattr('urllib.request.urlopen',lambda *a,**kw:Broken())
    with pytest.raises(OSError,match='dropped connection'):
        fetch_raw(tmp_path,progress=lambda *a:None)
    assert not list((tmp_path/'raw').iterdir())


def test_corrupt_download_is_never_committed(tmp_path,monkeypatch):
    import zipfile
    monkeypatch.setattr('urllib.request.urlopen',lambda *a,**kw:io.BytesIO(b'not a ZIP'))
    with pytest.raises(zipfile.BadZipFile):
        fetch_raw(tmp_path,progress=lambda *a:None)
    assert not list((tmp_path/'raw').iterdir())
