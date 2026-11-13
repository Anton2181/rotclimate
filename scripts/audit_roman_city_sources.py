"""Audit the official Hanson2016 Cities/Areas CSV tables and the exact-key housing join.

Declared in calibration/roman_city_source_recovery_20261113/plan.json (ab66b509).
Raw third-party rows stay in the ignored cache; only aggregates are written.
No model fit, score or measurement-gate change happens here.
"""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/cache/roman_city_source_recovery_20261113'
PLAN = ROOT / 'calibration/roman_city_source_recovery_20261113/plan.json'
HOUSING = ROOT / 'data/source/roman_housing_2023/table2.csv'
OUT = ROOT / 'output/roman_city_source_recovery_20261113'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(text):
    try:
        return float(text)
    except ValueError:
        return None


def read_tables():
    plan = json.loads(PLAN.read_text())
    pinned = {s['url'].rsplit('_', 2)[-2].lower(): s for s in plan['sources']}
    for name in ('cities', 'areas'):
        path = CACHE / f'{name}.csv'
        if sha(path) != pinned[name]['sha256'] or path.stat().st_size != pinned[name]['bytes']:
            raise ValueError(f'{name}.csv is not the pinned official table')
    cities = list(csv.DictReader(io.StringIO((CACHE / 'cities.csv').read_bytes().decode('cp1252'))))
    areas = list(csv.DictReader(io.StringIO((CACHE / 'areas.csv').read_bytes().decode('utf-8-sig'))))
    return cities, areas


def basis_class(text):
    """Coarse, order-dependent reading of the free-text Estimate Basis."""
    t = text.lower()
    for word, label in (('inhabited', 'inhabited_area'), ('grid', 'urban_grid'), ('wall', 'walls'),
                        ('rampart', 'walls'), ('fortif', 'walls'), ('range', 'range'), ('extent', 'extent')):
        if word in t:
            return label
    return 'other_or_unspecified' if t.strip() else 'blank'


def audit():
    cities, areas = read_tables()
    ckeys = [r['Primary Key'] for r in cities]; akeys = [r['Primary Key'] for r in areas]
    cset = set(ckeys)
    start = [number(r['Start Date']) for r in cities]; end = [number(r['End Date']) for r in cities]
    lon = [number(r['Longitude (X)']) for r in cities]; lat = [number(r['Latitude (Y)']) for r in cities]
    area = [number(r['Area']) for r in areas]
    numeric_area = [a for a in area if a is not None]
    covers = lambda s, e, year: s is not None and s <= year and (e is None or e >= year)
    cover150 = {k for k, s, e in zip(ckeys, start, end) if covers(s, e, 150)}
    area_by_key = {r['Primary Key']: number(r['Area']) for r in areas}
    positive = {k for k, a in area_by_key.items() if a is not None and a > 0}
    default_like = {k for k in positive if area_by_key[k] in (20.0, 30.0)}
    housing = list(csv.DictReader(HOUSING.open(encoding='utf-8')))
    by_key = {r['Primary Key']: r for r in cities}
    join = []
    for h in housing:
        key = f"Hanson2016_{h['city_key']}"
        c = by_key.get(key)
        a = area_by_key.get(key)
        site = float(h['site_area_ha'])
        join.append(dict(
            key_found=c is not None,
            name_exact=bool(c) and c['Ancient Toponym'].strip().lower() == h['ancient_name'].strip().lower(),
            province_exact=bool(c) and c['Province'].strip().lower() == h['province'].strip().lower(),
            area_record=a is not None,
            area_equal=a is not None and abs(a - site) <= 1e-9,
            area_ratio=None if not a else site / a,
            catalogue_covers_AD150=bool(c) and key in cover150,
            end_known=bool(c) and number(c['End Date']) is not None))
    ratios = sorted(j['area_ratio'] for j in join if j['area_ratio'] is not None and not j['area_equal'])
    result = dict(
        status='official_tables_audited_preparation_only_no_model_scores',
        declaration=str(PLAN.relative_to(ROOT)), declaration_sha256=sha(PLAN),
        producer_sha256=sha(__file__),
        sources={n: sha(CACHE / f'{n}.csv') for n in ('cities', 'areas')},
        housing_table_sha256=sha(HOUSING),
        cities=dict(
            rows=len(cities), unique_keys=len(cset), duplicate_keys=len(ckeys) - len(cset),
            key_pattern_ok=sum(k.startswith('Hanson2016_') and k[11:].isdigit() for k in ckeys),
            provinces=len({r['Province'] for r in cities}), countries=len({r['Country'] for r in cities}),
            start_numeric=sum(s is not None for s in start), end_numeric=sum(e is not None for e in end),
            end_null_text=sum(r['End Date'].strip().upper() == 'NULL' for r in cities),
            reversed_dates=sum(s is not None and e is not None and e < s for s, e in zip(start, end)),
            coordinates_numeric=sum(a is not None and b is not None for a, b in zip(lon, lat)),
            lon_range=[min(v for v in lon if v is not None), max(v for v in lon if v is not None)],
            lat_range=[min(v for v in lat if v is not None), max(v for v in lat if v is not None)],
            duplicate_coordinate_pairs=len(cities) - len({(a, b) for a, b in zip(lon, lat)}),
            duplicate_name_province_pairs=len(cities) - len({(r['Ancient Toponym'].strip().lower(), r['Province'].strip().lower()) for r in cities}),
            barrington_rank=dict(sorted(Counter(r['Barrington Atlas Rank'].strip() or 'blank' for r in cities).items())),
            catalogue_interval_contains_AD150=len(cover150),
            contains_AD150_with_known_end=sum(k in cover150 and e is not None for k, e in zip(ckeys, end)),
            start_after_AD150=sum(s is not None and s > 150 for s in start),
            end_before_AD150=sum(e is not None and e < 150 for e in end)),
        areas=dict(
            rows=len(areas), unique_keys=len(set(akeys)), duplicate_keys=len(akeys) - len(set(akeys)),
            orphan_keys=sum(k not in cset for k in akeys),
            numeric=len(numeric_area), nonnumeric=len(area) - len(numeric_area),
            positive=len(positive), zero_or_negative=sum(a is not None and a <= 0 for a in area),
            default_like_20_or_30_ha=len(default_like),
            quantiles_ha={q: sorted(numeric_area)[min(len(numeric_area) - 1, int(q * len(numeric_area)))]
                          for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
            minimum_ha=min(numeric_area), maximum_ha=max(numeric_area),
            basis_classes=dict(sorted(Counter(basis_class(r['Estimate Basis']) for r in areas).items())),
            distinct_basis_strings=len({r['Estimate Basis'] for r in areas}),
            cities_without_area_record=len(cset - set(akeys)),
            positive_area_and_catalogue_AD150=len(positive & cover150),
            positive_non_default_and_catalogue_AD150=len((positive - default_like) & cover150)),
        housing_join=dict(
            rows=len(join), key_found=sum(j['key_found'] for j in join),
            unmatched_keys=sum(not j['key_found'] for j in join),
            name_exact=sum(j['name_exact'] for j in join), name_conflicts=sum(j['key_found'] and not j['name_exact'] for j in join),
            province_exact=sum(j['province_exact'] for j in join),
            province_conflicts=sum(j['key_found'] and not j['province_exact'] for j in join),
            area_record=sum(j['area_record'] for j in join), area_equal=sum(j['area_equal'] for j in join),
            area_different=sum(j['area_record'] and not j['area_equal'] for j in join),
            area_missing=sum(j['key_found'] and not j['area_record'] for j in join),
            different_area_ratio_range=[ratios[0], ratios[-1]] if ratios else None,
            catalogue_covers_AD150=sum(j['catalogue_covers_AD150'] for j in join),
            end_date_known=sum(j['end_known'] for j in join)),
        measurement_gates=dict(
            qualified_AD150_housing_labels=0,
            reason='Catalogue Start/End dates describe the city record, not the excavated housing sample; Areas carries no phase field. '
                   'Identity recovery changes neither the 3 incompatible/47 unresolved sample phases nor representativeness/extent gates.'),
        raw_rows_redistributed=False, model_scores_computed=False)
    return result


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / 'audit.json').write_text(json.dumps(audit(), indent=1, sort_keys=True) + '\n')
    print(json.dumps(audit(), indent=1, sort_keys=True))
