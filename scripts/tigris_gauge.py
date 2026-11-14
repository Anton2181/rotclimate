"""Qualify Tigris gauges on the Hit source rules; phase preflight only, no field run.

calibration/tigris_gauge_20261114/plan.json. Reuses the seasonality step's
parser, complete-year rule and phase primitive unchanged.
"""
import argparse, csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from flood_basin_seasonality import GaugeTable, complete_years
from harvest.flood_timing import crop_flood_timing
from land_people import DAYS
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/tigris_gauge_20261114/plan.json'
CACHE = ROOT / 'data/cache/tigris_gauge_20261114'; OUT = ROOT / 'output/tigris_gauge_20261114'
OLD = ROOT / 'output/flood_basin_seasonality_20261113'; OLDCACHE = ROOT / 'data/cache/flood_basin_seasonality_20261113'
SOURCES = {
    'mosul.html': dict(url='https://doi.pangaea.de/10.1594/PANGAEA.218902?format=html', sha256='02825db96236f1bd77aaf4393a97c6682c719ccb5eb798211a1e9281b78334ba',
                       citation='Vörösmarty, Fekete & Tucker (2004), Tigris at Mosul monthly discharge, PANGAEA.218902; RivDIS (1998), doi:10.3334/ORNLDAAC/199', license='CC-BY-3.0'),
    'baghdad.html': dict(url='https://doi.pangaea.de/10.1594/PANGAEA.218359?format=html', sha256='a020c9ff4739eca13ed82267b754cb53cf186c799be2d5eff57273a0ff6321b9',
                         citation='Vörösmarty, Fekete & Tucker (2004), Tigris at Baghdad monthly discharge, PANGAEA.218359; RivDIS (1998), doi:10.3334/ORNLDAAC/199', license='CC-BY-3.0'),
}


def fetch():
    import hashlib, urllib.request
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, spec in SOURCES.items():
        path = CACHE / name
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(spec['url'], headers={'User-Agent': 'rotclimate-source-audit/1.0'}), timeout=90) as r: path.write_bytes(r.read())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256'], f'Publisher bytes changed: {name}; audit before reuse'


def gauge(path, years):
    parser = GaugeTable(); parser.feed(path.read_text()); rows = parser.rows
    assert rows and all(len(v) == 2 for v in rows) and len({v[0] for v in rows}) == len(rows)
    complete, flow, excluded = complete_years(rows, *years)
    return rows, complete, flow, excluded


def excess_km3(mean):
    """Positive excess above the annual monthly mean, as the field runs use for river source (km3/yr)."""
    return float(np.sum(np.maximum(mean - mean.mean(), 0) * DAYS * 86400) / 1e9)


def summary(flow):
    mean = flow.mean(axis=0); r = crop_flood_timing(mean, crop_months=5)
    return dict(years=int(len(flow)), mean_annual_flow_m3s=float(mean.mean()), annual_volume_km3=float(np.sum(mean * DAYS * 86400) / 1e9),
                peak_month=int(mean.argmax()) + 1, positive_excess_km3=excess_km3(mean),
                november_5_month={n: float(r[n][10]) for n in ('pre_sowing_excess_share', 'standing_crop_excess_share', 'compatibility')})


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    fetch(); plan = json.loads(PLAN.read_text()); out.mkdir(parents=True, exist_ok=True)
    old = json.loads((OLD / 'results.json').read_text()); protected = {f'output/flood_basin_seasonality_20261113/{k}': v for k, v in old['files_sha256'].items()}
    protected.update({k: v for k, v in old['producers'].items()})
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, 'Existing seasonality changed: ' + name
    controls = subprocess.run([str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', 'tests/test_flood_timing.py', 'tests/test_flood_gauge_quality.py'],
                              cwd=ROOT, capture_output=True, text=True, check=True)
    rows = []; fields = {}; raw = []; series = {}
    for spec in plan['sources']:
        key = spec['id']; rows_, years, flow, excluded = gauge(CACHE / f'{key}.html', spec['primary_years'])
        raw.extend([key, *v] for v in rows_); qualified = len(years) >= 5
        item = dict(id=key, doi=spec['doi'], role=spec['role'], source_rows=len(rows_), source_date_min=min(v[0] for v in rows_), source_date_max=max(v[0] for v in rows_),
                    primary_years=spec['primary_years'], complete_years=years, excluded_years=[e for e in excluded if e['records'] > 0],
                    years_without_records=sum(1 for e in excluded if e['records'] == 0), qualified=qualified)
        if qualified:
            series[key] = (years, flow); mean = flow.mean(axis=0)
            fields[key + '__complete_years'] = np.asarray(years); fields[key + '__monthly_flow'] = flow; fields[key + '__mean_flow'] = mean
            item.update(mean_monthly_flow_m3s=mean.tolist(), **summary(flow), phase=[])
            for duration in range(3, 10):
                r = crop_flood_timing(mean, crop_months=duration)
                for name, value in r.items(): fields[f'{key}__crop{duration}__{name}'] = value
                item['phase'].append(dict(crop_months=duration, **{n: v.tolist() for n, v in r.items()}))
        rows.append(item)
    hit_rows = GaugeTable(); hit_rows.feed((OLDCACHE / 'hit.html').read_text())
    hit_spec = next(v for v in json.loads((ROOT / 'calibration/flood_basin_seasonality_20261113/plan.json').read_text())['sources'] if v['id'] == 'hit')
    hy, hf, _ = complete_years(hit_rows.rows, *hit_spec['primary_years'])
    hit_archived = next(v for v in old['rows'] if v['id'] == 'hit')
    assert hy == hit_archived['complete_years'] and np.allclose(hf.mean(0), hit_archived['mean_monthly_flow_m3s'])
    comparison = dict(hit_own_years=dict(complete_years=hy, **summary(hf)))
    if 'mosul' in series:
        my, mf = series['mosul']; common = sorted(set(my) & set(hy))
        comparison['mosul_own_years'] = dict(complete_years=my, **summary(mf))
        if len(common) >= 5:
            pick = lambda years, flow: flow[[years.index(y) for y in common]]
            comparison['common_years'] = dict(years=common, hit=summary(pick(hy, hf)), mosul=summary(pick(my, mf)))
            both = pick(hy, hf) + pick(my, mf); comparison['common_years']['hit_plus_mosul'] = summary(both)
            fields['hit_plus_mosul__common_mean_flow'] = both.mean(axis=0); fields['common_years'] = np.asarray(common)
    np.savez_compressed(out / 'fields.npz', **fields)
    b = io.StringIO(newline=''); w = csv.writer(b); w.writerow(['station', 'crop_months', 'sowing_month', 'pre_sowing_excess_share', 'standing_crop_excess_share', 'compatibility'])
    for r in rows:
        for phase in r.get('phase', []):
            for sow in range(12): w.writerow([r['id'], phase['crop_months'], sow + 1, *[phase[n][sow] for n in ('pre_sowing_excess_share', 'standing_crop_excess_share', 'compatibility')]])
    (out / 'phase.csv').write_text(b.getvalue())
    b = io.StringIO(newline=''); w = csv.writer(b); w.writerow(['station', 'date', 'monthly_mean_m3s']); w.writerows(raw); (out / 'gauge_monthly.csv').write_text(b.getvalue())
    write(out / 'sources.json', SOURCES)
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, 'Existing seasonality changed during run: ' + name
    atlas = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'atlases/earth_fit').rglob('*')) if p.is_file()}
    write(out / 'results.json', dict(status='tigris_gauge_phase_preflight_only', rows=rows, comparison=comparison,
        controls=dict(status='passed_before_outputs', summary=controls.stdout.strip().splitlines()[-1].split(' in ')[0]),
        sources={str((CACHE / n).relative_to(ROOT)): s['sha256'] for n, s in SOURCES.items()},
        producers={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, ROOT / 'scripts/flood_basin_seasonality.py', ROOT / 'harvest/flood_timing.py']},
        files_sha256={n: sha(out / n) for n in ('fields.npz', 'phase.csv', 'gauge_monthly.csv', 'sources.json')}, unchanged_sha256=protected,
        unchanged_atlas_files=len(atlas), unchanged_atlas_digest=sha_of(atlas), field_runs=False, adopt=False,
        limits='Mosul lies upstream of the Greater and Lesser Zab, Adhaim and Diyala; it understates lower-Tigris flow and is not scaled. 1964-1972 is modern flow, not an ancient reconstruction.'))
    print(json.dumps({r['id']: (len(r['complete_years']), r['qualified'], r.get('peak_month'), r.get('positive_excess_km3')) for r in rows}))
    print(json.dumps(comparison, indent=1)[:2500])


def sha_of(mapping):
    import hashlib
    return hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
