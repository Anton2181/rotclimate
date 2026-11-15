"""Capital-effect development check (calibration/capital_effect_20261115/plan.json, A1)."""
import csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_release2_earth as R
from polity.survey_transfer import sphere_distance
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/capital_effect_20261115/plan.json'; OUT = ROOT / 'output/capital_effect_20261115'
WD = ROOT / 'data/cache/roman_capitals/wikidata.json'; FIT = ROOT / 'output/sizes_greek_walls_20261114/results.json'
ALIAS = {'Roman Britain': ['Britannia'], 'Britannia Inferior': ['Britannia'], 'Britannia Superior': ['Britannia'], 'Roman Egypt': ['Aegyptus'],
         'Africa': ['Africa Proconsularis'], 'Arabia Petraea': ['Arabia'], 'Hispania Baetica': ['Baetica'], 'Cappadocia': ['Cappadocia et Galatia'],
         'Galatia': ['Cappadocia et Galatia'], 'Cilicia': ['Cilicia et Cyprus', 'Silicia'], 'Cyprus': ['Cilicia et Cyprus', 'Silicia'],
         'Corsica and Sardinia': ['Corsica et Sardinia'], 'Alpes Poeninae': ['Alpes Graiae et Poeninae'], 'Roman Syria': ['Syria'],
         'Syria Palaestina': ['Syria Palestina'], 'Lower Pannonia': ['Pannonia Inferior']}
GREEK = {'Achaea', 'Macedonia', 'Epirus'}; ROME = (41.8925, 12.4853)


def year(b, k):
    v = b.get(k, {}).get('value')
    return None if not v else (int(v[:5]) if v[0] == '-' else int(v[:4]))


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True)
    basis = {r['Primary Key']: r['Estimate Basis'] for r in csv.DictReader(io.StringIO((R.CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    city = {r['Primary Key']: r for r in csv.DictReader(io.StringIO((R.CACHE / 'cities.csv').read_bytes().decode('cp1252')))}
    rows, _, _ = R.cohort(); hanson_prov = {r['province'] for r in rows}
    rows = [dict(r) for r in rows if r['area'] not in (20.0, 30.0)]
    for r in rows:
        if r['province'] in GREEK and basis.get(r['key'], '').startswith('Walls'): r['area'] *= 1 / 3 if r['area'] >= 100 else 1 / 2
        c = city[r['key']]; r['lat'] = float(c['Latitude (Y)']); r['lon'] = float(c['Longitude (X)']); r['name'] = c['Ancient Toponym']
    fit = json.loads(FIT.read_text())['sizes']['primary']['models']['M1']['full_coefficients']
    res = np.array([np.log(r['area']) - (fit[0] + fit[1] * r['lnH']) for r in rows]); area = np.array([r['area'] for r in rows])
    lat = np.array([r['lat'] for r in rows]); lon = np.array([r['lon'] for r in rows])
    caps = []
    for b in json.loads(WD.read_text())['results']['bindings']:
        label = b['provLabel']['value']; s, e = year(b, 'inception') or year(b, 'start'), year(b, 'end')
        if (s is not None and s > 150) or (e is not None and e < 150) or 'coord' not in b: continue
        targets = ALIAS.get(label, [label] if label in hanson_prov else [])
        if not targets: continue
        lo_, la_ = map(float, b['coord']['value'][6:-1].split()); caps.append(dict(province=label, capital=b['capLabel']['value'], lat=la_, lon=lo_))
    caps.append(dict(province='Italia (imperial capital)', capital='Rome', lat=ROME[0], lon=ROME[1]))
    matched = {}
    for c in caps:
        d = sphere_distance(lat, lon, c['lat'], c['lon']); i = int(np.argmin(d))
        if d[i] <= 5.0: matched.setdefault(i, []).append(c)
    idx = np.array(sorted(matched)); is_cap = np.zeros(len(rows), bool); is_cap[idx] = True
    rng = np.random.default_rng(1)
    def summary(mask):
        a, b = res[mask], res[~mask]; eff = float(a.mean() - b.mean())
        boots = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(10000)]
        pct = np.array([(np.sum(area < area[i]) + .5 * np.sum(area == area[i])) / len(area) for i in np.flatnonzero(mask)])
        return dict(capitals=int(mask.sum()), effect_ln=eff, factor=float(np.exp(eff)), ci95=[float(np.quantile(boots, .025)), float(np.quantile(boots, .975))],
                    mean_area_percentile=float(pct.mean()), share_top14=float(np.mean(pct >= .86)), share_top5=float(np.mean(pct >= .95)))
    rome_i = [i for i, cs in matched.items() if any(c['capital'] == 'Rome' for c in cs)]
    no_rome = is_cap.copy(); no_rome[rome_i] = False
    out = dict(status='capital_effect_development_check', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), wikidata_sha256=sha(WD),
               cohort=len(rows), capitals_listed=len(caps), capitals_matched_towns=int(is_cap.sum()), interpretable=bool(is_cap.sum() >= 20),
               all=summary(is_cap), without_rome=summary(no_rome),
               matched=[dict(town=rows[i]['name'], province=rows[i]['province'], area_ha=float(area[i]), residual_ln=float(res[i]), via=[c['capital'] for c in cs]) for i, cs in sorted(matched.items())])
    write(OUT / 'results.json', out); print(json.dumps({k: v for k, v in out.items() if k != 'matched'}, indent=1))


if __name__ == '__main__':
    main()
