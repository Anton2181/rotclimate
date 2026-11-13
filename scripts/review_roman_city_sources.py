"""Independent pandas re-read of the official tables; compares every audit count."""
import hashlib, json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/cache/roman_city_source_recovery_20261113'
OUT = ROOT / 'output/roman_city_source_recovery_20261113'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

audit = json.loads((OUT / 'audit.json').read_text())
c = pd.read_csv(CACHE / 'cities.csv', encoding='cp1252', keep_default_na=False, dtype=str)
a = pd.read_csv(CACHE / 'areas.csv', encoding='utf-8-sig', keep_default_na=False, dtype=str)
h = pd.read_csv(ROOT / 'data/source/roman_housing_2023/table2.csv', dtype=str, keep_default_na=False)
start = pd.to_numeric(c['Start Date'], errors='coerce'); end = pd.to_numeric(c['End Date'], errors='coerce')
cover = (start <= 150) & (end.isna() | (end >= 150))
area = pd.to_numeric(a['Area'], errors='coerce')
m = c.assign(cover=cover).merge(a.assign(area=area), on='Primary Key', how='left', validate='one_to_one')
hj = h.assign(key='Hanson2016_' + h['city_key']).merge(m, left_on='key', right_on='Primary Key', how='left', validate='one_to_one')
checks = {
    'city_rows': (len(c), audit['cities']['rows']),
    'city_unique': (c['Primary Key'].nunique(), audit['cities']['unique_keys']),
    'area_rows': (len(a), audit['areas']['rows']),
    'orphans': (int((~a['Primary Key'].isin(c['Primary Key'])).sum()), audit['areas']['orphan_keys']),
    'cover150': (int(cover.sum()), audit['cities']['catalogue_interval_contains_AD150']),
    'end_numeric': (int(end.notna().sum()), audit['cities']['end_numeric']),
    'positive_area_cover150': (int((m['cover'] & (m['area'] > 0)).sum()), audit['areas']['positive_area_and_catalogue_AD150']),
    'nondefault_cover150': (int((m['cover'] & (m['area'] > 0) & ~m['area'].isin([20, 30])).sum()), audit['areas']['positive_non_default_and_catalogue_AD150']),
    'no_area': (int(m['area'].isna().sum()), audit['areas']['cities_without_area_record']),
    'median_ha': (float(area.sort_values().iloc[int(.5 * len(area))]), audit['areas']['quantiles_ha']['0.5']),
    'max_ha': (float(area.max()), audit['areas']['maximum_ha']),
    'housing_found': (int(hj['Primary Key'].notna().sum()), audit['housing_join']['key_found']),
    'housing_name_exact': (int((hj['Ancient Toponym'].str.strip().str.lower() == hj['ancient_name'].str.strip().str.lower()).sum()), audit['housing_join']['name_exact']),
    'housing_area_equal': (int((hj['area'] == pd.to_numeric(hj['site_area_ha'])).sum()), audit['housing_join']['area_equal']),
    'housing_cover150': (int(hj['cover'].sum()), audit['housing_join']['catalogue_covers_AD150']),
}
bad = {k: v for k, v in checks.items() if v[0] != v[1]}
result = dict(status='passed' if not bad else 'failed', checks=len(checks), mismatches=bad,
              audit_sha256=sha(OUT / 'audit.json'), reviewer_sha256=sha(__file__))
(OUT / 'review.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
print(result); sys.exit(bool(bad))
