"""Offline weather-format, covariance, bounded-download and resume checks."""
from datetime import datetime
import io
import urllib.error
import numpy as np
import pytest
from experiments import v10_weather_audit as w
from scripts import audit_v10_weather as runner


def das(variable='air', units='degK', packed=False):
    packing = 'Float32 scale_factor 0.01; Float32 add_offset 477.65; Int16 missing_value 32767;' if packed else ''
    return ('Attributes { NC_GLOBAL { String dataset_title "NCEP-NCAR Reanalysis 1"; } '
        'time { String units "hours since 1800-01-01 00:00:0.0"; } '
        'level { String units "millibar"; } '+variable+' { String units "'+units+'"; '
        'String statistic "Individual Obs"; '+packing+' } }')


def job(variable='air'):
    return {'kind': 'data', 'variable': variable, 'year': 2000, 'month': 1, 'box': [18, 19, 90, 91],
        'count': 124, 'name': variable+'_2000_01_test.ascii', 'url': w.BASE+'test.ascii'}


def payload(j, value):
    variable = j['variable'];n = j['count']
    lines = ['Dataset {}', '---------------------------------------------', f'{variable}.{variable}[{n}][7][2][2]']
    for time in range(n):
        for level in range(7):
            for lat in range(2):
                lines.append(f'[{time}][{level}][{lat}], {value}, {value}')
    axes = [('time', (datetime(j['year'], j['month'], 1)-datetime(1800, 1, 1)).total_seconds()/3600+6*np.arange(n)),
        ('level', w.LEVELS), ('lat', [45., 42.5]), ('lon', [225., 227.5])]
    for name, values in axes:
        lines += ['', f'{variable}.{name}[{len(values)}]', ', '.join(str(v) for v in values), '']
    return '\n'.join(lines)+'\n'


def test_declared_requests_are_bounded_regional_six_hourly_and_leap_correct():
    plan = w.request_plan()
    assert len(plan) == 56
    assert sum(j['kind'] == 'data' for j in plan) == 48
    assert w.time_slice(1990, 7) == (724, 847, 124)
    assert w.time_slice(2000, 7) == (728, 851, 124)
    assert all('[1:1:7]' in j['url'] for j in plan if j['kind'] == 'data')
    assert all(j['url'].startswith(w.BASE) for j in plan)


def test_packed_temperature_is_decoded_before_kelvin_conversion():
    j = job()
    attrs = w.metadata(das(packed=True), 'air')
    field = w.decode(payload(j, -20000), attrs, j)
    np.testing.assert_allclose(field.values, 4.5, atol=1e-10)
    missing = w.decode(payload(j, 32767), attrs, j)
    assert np.isnan(missing.values).all()


def test_specific_humidity_kept_specific_and_time_mismatch_rejected():
    j = job('shum');attrs = w.metadata(das('shum', 'kg/kg'), 'shum')
    field = w.decode(payload(j, .004), attrs, j)
    np.testing.assert_allclose(field.values, .004)
    wrong = dict(j, year=1990)
    with pytest.raises(ValueError, match='dates'):
        w.decode(payload(j, .004), attrs, wrong)


def test_daily_means_and_climatology_are_rejected_as_weather():
    with pytest.raises(ValueError, match='individual'):
        w.metadata(das().replace('Individual Obs', 'Mean'), 'air')
    with pytest.raises(ValueError, match='climatology'):
        w.metadata(das()+' String climo_period "1981-2010";', 'air')
    with pytest.raises(ValueError, match='origin'):
        w.metadata(das().replace('1800-01-01', '2000-01-01'), 'air')


def field(values):
    return w.monthly.Field(values, w.LEVELS, np.array([40.]), np.array([230., 232.5]), np.arange(len(values))*6.)


def test_temporal_covariance_distinguishes_weather_with_identical_means():
    q = np.broadcast_to(np.array([.002, .006, .002, .006])[:, None, None, None], (4, 7, 1, 2)).copy()
    u = np.broadcast_to(np.array([2., 6., 2., 6.])[:, None, None, None], q.shape).copy()
    t = np.broadcast_to(np.array([10., 20., 10., 20.])[:, None, None, None], q.shape).copy()
    fields = dict(shum=field(q), uwnd=field(u), vwnd=field(np.zeros_like(u)), air=field(t))
    selected = np.ones((1, 2), bool);weights = np.array([.5, .5])
    result = w.diagnose(fields, selected, weights)
    positive = result['transport']['eastward']
    scale = (925-300)*100/w.G
    assert positive['full_mean_kg_m_s'] == pytest.approx(.020*scale)
    assert positive['product_of_means_kg_m_s'] == pytest.approx(.016*scale)
    assert positive['temporal_covariance_kg_m_s'] == pytest.approx(.004*scale)
    assert result['top_decile_925hpa_specific_humidity_anomaly_g_kg'] == pytest.approx(2.)
    assert result['top_decile_925hpa_temperature_anomaly_c'] == pytest.approx(5.)
    fields['uwnd'] = field(u[::-1])
    negative = w.diagnose(fields, selected, weights)['transport']['eastward']
    assert negative['product_of_means_kg_m_s'] == pytest.approx(positive['product_of_means_kg_m_s'])
    assert negative['temporal_covariance_kg_m_s'] == pytest.approx(-.004*scale)


def test_uniform_humidity_has_no_temporal_flux_covariance():
    q = np.full((4, 7, 1, 2), .004)
    u = np.broadcast_to(np.arange(4.)[:, None, None, None], q.shape)
    fields = dict(shum=field(q), uwnd=field(u), vwnd=field(u*0), air=field(u*0+15.))
    result = w.diagnose(fields, np.ones((1, 2), bool), np.array([.5, .5]))
    assert abs(result['transport']['eastward']['temporal_covariance_kg_m_s']) < 1e-10


def test_downloader_stops_on_rate_limit_without_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'request_plan', lambda: [dict(job(), kind='metadata', name='air_2000.das')])
    calls = []
    def busy(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError(w.BASE, 429, 'Too Many Requests', {'Retry-After': '60'}, None)
    monkeypatch.setattr(w.urllib.request, 'urlopen', busy)
    with pytest.raises(w.ServerPaused, match='Retry-After: 60'):
        w.acquire(tmp_path, fetch=True)
    assert len(calls) == 1 and not (tmp_path/'downloads.json').exists()


def test_cached_requests_resume_and_corruption_is_refused(tmp_path, monkeypatch):
    data_job = job()
    metadata_job = dict(data_job, kind='metadata', name='air_2000.das', url=w.BASE+'air.2000.nc.das')
    monkeypatch.setattr(w, 'request_plan', lambda: [metadata_job, data_job])
    responses = [das().encode(), payload(data_job, 280.).encode()]
    calls = []
    def fetch(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(responses[len(calls)-1])
    monkeypatch.setattr(w.urllib.request, 'urlopen', fetch)
    records, saved = w.acquire(tmp_path, fetch=True, spacing_seconds=0.)
    assert len(calls) == 2
    again, _ = w.acquire(tmp_path, fetch=False)
    np.testing.assert_allclose(again[data_job['name']].values, records[data_job['name']].values)
    assert len(calls) == 2
    (tmp_path/data_job['name']).write_text('corrupt')
    with pytest.raises(ValueError, match='provenance'):
        w.acquire(tmp_path, fetch=True)
    assert len(calls) == 2


def test_default_is_read_only_even_with_fetch_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected download/model run'))
    out = tmp_path/'absent';cache = tmp_path/'cache'
    assert runner.main(['--fetch', '--out', str(out), '--cache', str(cache)]) == 0
    assert not out.exists() and not cache.exists()


def test_runner_records_pause_without_fabricating_statistics(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'prepare', lambda: ({'code_sha256': runner.source_id()}, {}))
    monkeypatch.setattr(w, 'acquire', lambda *a, **k: (_ for _ in ()).throw(w.ServerPaused('HTTP 429; resume later')))
    result = runner.run(tmp_path/'out', tmp_path/'cache', fetch=True)
    assert result['status'] == 'fetch_paused' and not result['windows']
    assert result['climate_integrations'] == 0
