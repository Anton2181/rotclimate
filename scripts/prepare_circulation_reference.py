"""Validate downloaded public surface wind/SLP data; no climate integrations."""
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/circulation_reference_20261127'
BASE = 'https://psl.noaa.gov/thredds/fileServer/Datasets/ncep.reanalysis.derived/surface/'
FIELDS = dict(u=('uwnd.sig995.mon.ltm.nc', 'uwnd'), v=('vwnd.sig995.mon.ltm.nc', 'vwnd'), slp_pa=('slp.mon.ltm.nc', 'slp'))


def string(value):
    return value.decode() if isinstance(value, bytes) else str(value)


def main():
    arrays, sources = {}, {}
    period = None
    for key, (name, variable) in FIELDS.items():
        path = OUT / name
        with h5py.File(path, 'r') as f:
            source = f[variable]
            raw = np.asarray(source[...], float)
            assert raw.shape == (12, 73, 144) and np.isfinite(raw).all()
            for missing in ['missing_value', '_FillValue']:
                if missing in source.attrs:
                    assert not np.isin(raw, np.atleast_1d(source.attrs[missing])).any()
            value = raw * float(np.asarray(source.attrs.get('scale_factor', 1.)).item())
            value += float(np.asarray(source.attrs.get('add_offset', 0.)).item())
            units = string(source.attrs['units'])
            factor = 1.
            if key == 'slp_pa':
                if units.lower() in ['millibars', 'hpa', 'mb']:
                    factor = 100.
                else:
                    assert units.lower() in ['pa', 'pascals']
                value *= factor
                assert np.all((value > 80000) & (value < 115000))
            else:
                assert units == 'm/s' and np.max(np.abs(value)) < 103
                assert string(source.attrs['level_desc']) == '0.995 sigma'
            np.testing.assert_array_equal(f['lat'][...], 90 - 2.5 * np.arange(73))
            np.testing.assert_array_equal(f['lon'][...], 2.5 * np.arange(144))
            found_period = string(f['time'].attrs['climo_period'])
            assert found_period == '1991/01/01 - 2020/12/31'
            if period is None:
                period = found_period
            assert found_period == period
            arrays[key] = value
            sources[key] = dict(url=BASE + name, file=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                variable=variable, source_units=units, normalization_factor=factor,
                normalized_units='Pa' if key == 'slp_pa' else 'm/s', shape=list(value.shape),
                level=string(source.attrs.get('level_desc', 'mean sea level')),
                period=period, title=string(f.attrs.get('title', '')), bounds_hours=np.asarray(f['climatology_bounds'][...]).tolist())
    packet = OUT / 'surface_reference.npz'
    assert not packet.exists(), 'Preserve prepared reference'
    np.savez_compressed(packet, lat=90 - 2.5*np.arange(73), lon=2.5*np.arange(144), **arrays)
    (OUT / 'sources.json').write_text(json.dumps(dict(status='validated_public_diagnostic_reference_not_model_forcing',
        sources=sources, packet_sha256=hashlib.sha256(packet.read_bytes()).hexdigest(),
        preparer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        provenance='NOAA PSL NCEP/NCAR Reanalysis 1; surface sigma0.995 wind and mean sea-level pressure, 1991-2020 monthly climatology. Full pressure is not the model thermal pressure anomaly.',
        retrieval='downloads.psl.noaa.gov timed out without writing data. NOAA PSL THREDDS fileServer succeeded; a 429 response was recovered with a delayed request. No climate runs were retried.',
        climate_integrations=0), indent=2) + '\n')
    print('Validated surface sigma0.995 wind and pressure; converted millibars to Pa; no forcing/integrations')


if __name__ == '__main__':
    main()
