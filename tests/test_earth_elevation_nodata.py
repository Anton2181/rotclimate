import io
import zipfile
import numpy as np
from PIL import Image, TiffImagePlugin
from scripts import land_people_earth as earth


def test_declared_marine_nodata_does_not_create_a_false_coastal_cliff(tmp_path,monkeypatch):
    elevation=np.array([[-32768,2,3],[-32768,2,3],[-32768,2,3]],dtype=np.int16)
    tags=TiffImagePlugin.ImageFileDirectory_v2();tags[42113]='-32768'
    f=io.BytesIO();Image.fromarray(elevation).save(f,format='TIFF',tiffinfo=tags)
    with zipfile.ZipFile(tmp_path/'wc2.1_5m_elev.zip','w') as archive:archive.writestr('wc2.1_5m_elev.tif',f.getvalue())
    monkeypatch.setattr(earth,'WC',tmp_path)
    decoded=earth.wc('elev');assert np.isnan(decoded[:,0]).all()
    arable,relief=earth.arable_share(decoded)
    assert relief.max()==3 and np.all(arable==np.float32(.85))


def test_legitimate_negative_elevation_and_zero_are_preserved(tmp_path,monkeypatch):
    elevation=np.array([[-430,0,20]],dtype=np.int16)
    tags=TiffImagePlugin.ImageFileDirectory_v2();tags[42113]='-32768'
    f=io.BytesIO();Image.fromarray(elevation).save(f,format='TIFF',tiffinfo=tags)
    with zipfile.ZipFile(tmp_path/'wc2.1_5m_elev.zip','w') as archive:archive.writestr('wc2.1_5m_elev.tif',f.getvalue())
    monkeypatch.setattr(earth,'WC',tmp_path)
    np.testing.assert_array_equal(earth.wc('elev'),elevation)
