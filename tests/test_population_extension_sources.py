import struct
import numpy as np
import pytest
from scripts.prepare_population_extension import decode_etopo_grid


def payload():
    header=b'Dataset { Grid { ARRAY: Float32 z[lat = 2][lon = 3]; MAPS: Float64 lat[lat = 2]; Float64 lon[lon = 3]; } z; } example;\nData:\n'
    data=[np.arange(6,dtype='>f4'),np.array([32.1,32.2],'>f8'),np.array([120.1,120.2,120.3],'>f8')]
    return header+b''.join(struct.pack('>II',len(a),len(a))+a.tobytes() for a in data)


def test_grid_coordinates_are_checked_as_well_as_elevation():
    z,lat,lon=decode_etopo_grid(payload(),2,3)
    np.testing.assert_array_equal(z,[[0,1,2],[3,4,5]])
    np.testing.assert_allclose(lat,[32.1,32.2]);np.testing.assert_allclose(lon,[120.1,120.2,120.3])
    for bad in [payload()[:-1],payload()+b'extra',payload().replace(b'Float64 lat',b'Float32 lat')]:
        with pytest.raises(ValueError):decode_etopo_grid(bad,2,3)
    wrong=payload().replace(struct.pack('>II',2,2),struct.pack('>II',1,2))
    with pytest.raises(ValueError,match='array counts'):decode_etopo_grid(wrong,2,3)
