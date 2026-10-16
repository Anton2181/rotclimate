"""Reference parsing/units/provenance tests; no downloads or climate runs."""
import io
import json
from pathlib import Path
import re
import numpy as np
import pytest

from experiments import v10_forcing_audit as a
from scripts import audit_v10_forcing as runner
from rotclimate_v10.core import DAY,EDGES,Config,Domain
from rotclimate_v10.earth import EarthCase


LEVELS = np.array([1000,925,850,700,600,500,400,300,250,200,150,100,70,50,30,20,10.])
UNITS = {'air':'degC','hgt':'m','shum':'grams/kg','uwnd':'m/s','vwnd':'m/s','omega':'Pascal/s'}


def ascii_fixture(var='air',shape=(12,2,2,2),box=None,value=7.):
    nt,nz,ny,nx = shape
    lat = np.linspace(40,37.5,ny) if box is None else 90-2.5*np.arange(box[0],box[1]+1)
    lon = np.linspace(225,227.5,nx) if box is None else 2.5*np.arange(box[2],box[3]+1)
    times = -657073+EDGES[:nt]/DAY
    data = [f'{var}.{var}'+''.join(f'[{n}]' for n in shape)]
    for i in range(nt):
        for j in range(nz):
            for k in range(ny):data.append(f'[{i}][{j}][{k}], '+', '.join([str(value)]*nx))
    for name,axis in (('time',times),('level',LEVELS[:nz]),('lat',lat),('lon',lon)):
        data += ['',f'{var}.{name}[{len(axis)}]',', '.join(map(str,axis)),'']
    return 'Dataset { placeholder; }\n---------------------------------------------\n'+'\n'.join(data)+'\n\n'


def das_fixture(var):
    return ('Attributes { time { String climo_period "1981/01/01 - 2010/12/31"; } '+var+
            ' { String units "'+UNITS[var]+'"; Float32 scale_factor 1.0; Float32 add_offset 0.0; } }')


def field(value=10.):
    return a.Field(np.full((12,2,2,2),value),np.array([1000.,500.]),np.array([40.,30.]),np.array([0.,355.]),EDGES[:12]/DAY)


def test_ascii_grid_and_coordinate_maps():
    f = a.parse_ascii(ascii_fixture(),'air')
    assert f.values.shape==(12,2,2,2) and f.values.mean()==7
    np.testing.assert_array_equal(f.pressure_hpa,[1000.,925.])
    np.testing.assert_array_equal(f.latitude,[40.,37.5])
    np.testing.assert_array_equal(f.time-f.time[0],EDGES[:12]/DAY)


@pytest.mark.parametrize('damage',['row_missing','row_duplicate','truncated','wrong_month','html'])
def test_bad_ascii_is_rejected(damage):
    text = ascii_fixture()
    if damage=='row_missing':text = text.replace('[0][0][0], 7.0, 7.0\n','')
    elif damage=='row_duplicate':text = text.replace('[0][0][0], 7.0, 7.0\n','[0][0][0], 7.0, 7.0\n'*2)
    elif damage=='truncated':text = text.replace('[0][0][0], 7.0, 7.0','[0][0][0], 7.0')
    elif damage=='wrong_month':text = text.replace('-657073.0','-657072.0')
    else:text = '<html>error page</html>'
    with pytest.raises(ValueError):a.parse_ascii(text,'air')


def test_missing_sentinel_is_not_valid_climate_data():
    f = a.parse_ascii(ascii_fixture(value=-9.96921e36),'air')
    assert np.isnan(f.values).all()


def test_humidity_units_and_specific_to_dry_air_mixing_ratio():
    f = a.normalize(field(10.),'shum','grams/kg')
    np.testing.assert_allclose(f.values,.01/.99)
    np.testing.assert_allclose(a.normalize(field(.01),'shum','kg/kg').values,f.values)
    with pytest.raises(ValueError):a.normalize(field(10.),'shum','kg/kg')


def test_verified_omega_units_and_temperature_conversion():
    assert a.normalize(field(.05),'omega',a.metadata(das_fixture('omega'),'omega')).values.mean()==pytest.approx(.05)
    np.testing.assert_allclose(a.normalize(field(280.),'air','K').values,6.85)
    with pytest.raises(ValueError):a.normalize(field(.05),'omega','m/s')


def test_wrong_climatology_or_packing_rejected():
    for text in (das_fixture('air').replace('1981/01/01','1991/01/01'),das_fixture('air').replace('scale_factor 1.0','scale_factor .1')):
        with pytest.raises(ValueError):a.metadata(text,'air')


def test_log_pressure_interpolation_and_cyclic_longitude():
    f = field();f.values[:,0,:,:] = 10.;f.values[:,1,:,:] = 0.;f.values[:,:,:,1] += 20.
    val,iy,ix = a.at_pressure(f,np.array([[-5.,0.]]),np.array([[40.,30.]]),np.sqrt(500*1000))
    np.testing.assert_allclose(val[:,0,0],25.);np.testing.assert_allclose(val[:,0,1],5.)
    np.testing.assert_array_equal(ix,[[1,0]])
    with pytest.raises(ValueError,match='outside'):a.at_pressure(f,np.array([[0.]]),np.array([[40.]]),1100.)


def test_request_plan_has_only_bounded_regions_no_precipitation():
    plan = a.request_plan()
    assert len(plan)==24 and len([r for r in plan if r[-1] is not None])==18
    assert all('https://psl.noaa.gov/thredds/dodsC/' in r[1] for r in plan)
    assert all(r[2] in a.VARIABLES and 'precip' not in r[1] for r in plan)
    assert all('[0:1:11]' in url for _,url,_,box in plan if box)


def test_fetch_resume_and_cache_integrity(tmp_path,monkeypatch):
    # Two responses suffice to verify atomic caching and resume semantics.
    plan = [a.request_plan()[0],a.request_plan()[1]]
    monkeypatch.setattr(a,'request_plan',lambda:plan)
    requests = []
    def fake(req,**kw):
        requests.append(req.full_url)
        if req.full_url.endswith('.das'):return io.BytesIO(das_fixture('air').encode())
        box = plan[1][-1];shape = (12,17,box[1]-box[0]+1,box[3]-box[2]+1)
        return io.BytesIO(ascii_fixture(shape=shape,box=box).encode())
    monkeypatch.setattr('urllib.request.urlopen',fake)
    a.acquire(tmp_path,True,progress=lambda *args,**kw:None)
    assert len(requests)==2
    a.acquire(tmp_path,False)
    assert len(requests)==2
    (tmp_path/'air.das').write_text('changed')
    with pytest.raises(ValueError,match='cache changed'):a.acquire(tmp_path,False)


def test_bad_response_never_committed(tmp_path,monkeypatch):
    plan = a.request_plan()[:1];monkeypatch.setattr(a,'request_plan',lambda:plan)
    monkeypatch.setattr('urllib.request.urlopen',lambda *args,**kw:io.BytesIO(b'<html>error</html>'))
    with pytest.raises(ValueError):a.acquire(tmp_path,True,progress=lambda *args,**kw:None)
    assert list(tmp_path.iterdir())==[]


def test_reference_comparison_scores_only_offshore_pressure(tmp_path):
    ny,nx = 20,20
    lon,lat = np.meshgrid(np.linspace(-133,-120,nx),np.linspace(43,32,ny))
    land = np.zeros((ny,nx),bool);land[:,16:] = True
    elevation = np.where(land,10000.,0.)  # below-ground inland requests must not poison ocean comparison
    d = Domain('california',land,elevation,lat,np.full((12,ny,nx),15.),60000.,60000.)
    case = EarthCase(d,lon,np.ones((12,ny,nx)),land.copy(),np.zeros((ny,nx)),np.zeros((ny,nx),bool))
    fields = {}
    for variable in a.VARIABLES:
        values = np.zeros((12,17,7,11))
        if variable=='air':values += 10.
        if variable=='hgt':values += 1000.
        if variable=='shum':values += .005
        fields['california',variable] = a.Field(values,LEVELS,90-2.5*np.arange(18,25),2.5*np.arange(90,101),EDGES[:12]/DAY)
    result = a.reference_comparison(case,Config(),fields)
    assert result['ocean_model_cells']>0 and result['levels']['lower']['reference_unique_native_cells']<result['ocean_model_cells']
    assert result['levels']['lower']['air']==[10.]*12


def test_default_never_downloads_or_reads_runs(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'saved_analysis',lambda *args:pytest.fail('unexpected input processing'))
    assert runner.main(['--out',str(tmp_path/'out')])==0 and list(tmp_path.iterdir())==[]
