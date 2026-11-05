"""Observed-weather historical wheat benchmark; no production overrides.

The crop response is reused, but years are chronological, nonwrapping and
observed. A constant reference-soil bucket is not a crop-root water ledger.
"""
from calendar import monthrange
from collections import Counter, defaultdict
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import openpyxl

from harvest.crop_sequences import crop_windows
from scripts.land_people import CROPS, DAYS, hargreaves, sunlight_top

FACTORS = ('fym', 'rape_cake', 'n', 'p', 'k', 'na', 'mg')
MINERALS = ('n', 'p', 'k', 'na', 'mg')
FLOOR = .05


def plot_id(value):
    """Numeric identifiers have one canonical representation, including splits."""
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError('Invalid plot identity') from exc
    if not number.is_finite() or number <= 0:
        raise ValueError('Invalid plot identity')
    return format(number.normalize(), 'f')


def month_keys(start, end):
    first, last = start.year * 12 + start.month - 1, end.year * 12 + end.month - 1
    return [divmod(i, 12) for i in range(first, last + 1)]


def calendar_keys(start, end):
    return [(y, m + 1) for y, m in month_keys(start, end)]


def load_weather(cache, last_year, latitude):
    temp = openpyxl.load_workbook(Path(cache) / 'roth_temperature_0.xlsx', read_only=True, data_only=True)
    rain = openpyxl.load_workbook(Path(cache) / 'roth_rain_0.xlsx', read_only=True, data_only=True)
    # Each sheet also contains monthly extrema. Require the monthly MEAN block.
    for sheet, col in [('Tmean', 18), ('Tmax', 18), ('Tmin', 19)]:
        assert temp[sheet].cell(1, col).value == {'Tmean': 'Mean Temperature (Mean)', 'Tmax': 'Maximum Temperature (Mean)', 'Tmin': 'Minimum Temperature (Mean)'}[sheet]
        assert temp[sheet].cell(2, col + 1).value == 'Jan'

    def table(sheet, first_row, year_col, month_col):
        result = {}
        for row in sheet.iter_rows(min_row=first_row, values_only=True):
            year = row[year_col]
            if isinstance(year, (int, float)) and 1878 <= year <= last_year:
                for m in range(12):
                    value = row[month_col + m]
                    result[int(year), m + 1] = float(value) if value is not None else math.nan
        return result

    values = {name: table(temp[sheet], 3, 0, offset) for name, sheet, offset in [('T', 'Tmean', 18), ('Tmax', 'Tmax', 18), ('Tmin', 'Tmin', 19)]}
    values.update(P=table(rain['DATA'], 5, 0, 1), temperature_days=table(temp['DAYS'], 4, 1, 2), rain_days=table(rain['DAYS'], 4, 1, 2))
    temp.close(); rain.close()
    radiation = sunlight_top(np.array(latitude), 23.44, 355)
    soil = 50.
    weather = {}
    for year in range(1878, last_year + 1):
        for month in range(1, 13):
            key = (year, month)
            r = {name: series.get(key, math.nan) for name, series in values.items()}
            expected = monthrange(year, month)[1]
            dtr = r['Tmax'] - r['Tmin']
            r['valid'] = bool(all(math.isfinite(x) for x in r.values()) and r['P'] >= 0 and dtr >= 0 and expected - 1 <= r['temperature_days'] <= expected and 0 <= r['rain_days'] <= expected)
            r['temperature_missing_days'] = expected - r['temperature_days'] if math.isfinite(r['temperature_days']) else None
            r['rain_missing_days'] = expected - r['rain_days'] if math.isfinite(r['rain_days']) else None
            r['PET'] = float(hargreaves(r['T'], dtr, radiation[month - 1]))
            r['soil_start'] = soil
            soil = float(np.clip(soil + r['P'] - r['PET'], 0, 100))
            weather[key] = r
    return weather


def capacity(year, weather):
    keys = calendar_keys(date(year - 1, 9, 1), date(year, 8, 1))
    rows = [weather.get(k, {}) for k in keys]
    if not all(r.get('valid', False) and math.isfinite(r['soil_start']) for r in rows):
        return None
    inputs = [np.array([r[k] for r in rows]) for k in ('T', 'P', 'PET', 'soil_start')]
    crop = CROPS['wheat']
    catalogue = crop_windows(*inputs, 0., crops={'wheat': crop})
    indices = [i for i, w in enumerate(catalogue.windows) if w.start + w.length <= 12]
    best = max(indices, key=lambda i: catalogue.energy[i])
    window = catalogue.windows[best]
    gross = float(catalogue.energy[best] / (1000 * crop['edible'] * crop['kcal'] * (1 - crop['seed'])))
    missing = int(sum(r['rain_missing_days'] for r in rows))
    return dict(baseline_t_ha=gross, best_start=list(keys[window.start]), best_months=window.length,
                crop_year_start=list(keys[0]), crop_year_end=list(keys[-1]),
                temperature_missing_days=int(sum(r['temperature_missing_days'] for r in rows)),
                rain_missing_days=missing, trace_only_rain_bound_mm=.05 * missing)


def observed_calendar(sowing, harvest, year, weather):
    keys = calendar_keys(sowing, harvest)
    if not all(k in weather and weather[k]['valid'] for k in keys):
        return dict(available=False, months=len(keys))
    T = np.array([weather[k]['T'] for k in keys])
    crop = CROPS['wheat']
    failures = []
    if not crop['months'][0] <= len(keys) <= crop['months'][1]: failures.append('length')
    if not np.all((T >= crop['window'][0]) & (T <= crop['window'][1])): failures.append('temperature')
    if T.max() < crop['need_warm']: failures.append('warmest_month')
    if np.maximum(T - crop['base'], 0).sum() * DAYS < crop['heat']: failures.append('heat')
    return dict(available=True, months=len(keys), representable=not failures, failures=failures,
                minimum_temperature=float(T.min()), outside_fixed_crop_year=keys[0] < (year - 1, 9) or keys[-1] > (year, 8))


def treatment(row):
    factors = {k: row[k + '_factor_level'].strip() for k in FACTORS}
    if plot_id(row['plot']) == '3':
        if any(v != 'nil' for v in factors.values()):
            raise ValueError('Primary plot3 is not all-nil: source changed')
        return 'unmanured_plot3'
    if factors['fym'] != 'nil' and all(factors[k] == 'nil' for k in FACTORS if k != 'fym'):
        return 'fym_only'
    if factors['fym'] == factors['rape_cake'] == 'nil' and any(factors[k] != 'nil' for k in MINERALS):
        return 'mineral_only'
    return 'other_organic_or_mixed'


def assert_temporal_integrity(cases, plan):
    seen = set()
    year_folds = defaultdict(set)
    for c in cases:
        key = (c['year'], c['stratum'])
        if key in seen: raise ValueError('Duplicate aggregate year/stratum')
        seen.add(key); year_folds[c['year']].add(c['split'])
        expected = [s for s in ('training', 'evaluation') if plan['split'][s][0] <= c['year'] <= plan['split'][s][1]]
        if expected != [c['split']]: raise ValueError('Temporal split mismatch')
        if c['site_id'] != 'ERA:Broadbalk': raise ValueError('Unexpected site identity')
    if any(len(v) != 1 for v in year_folds.values()): raise ValueError('Year crosses folds')


def prepare(cache, plan):
    weather = load_weather(cache, plan['split']['evaluation'][1], plan['site']['latitude'])
    excluded = Counter(); groups = defaultdict(list); seen = set()
    with zipfile.ZipFile(Path(cache) / 'broadbalk_0.zip') as z:
        # This unit is present in Excel metadata, but omitted in the JSON schema.
        book = openpyxl.load_workbook(io.BytesIO(z.read('01-BKyield1852-1925.xlsx')), read_only=True, data_only=True)
        metadata = list(book['fields_metadata'].iter_rows(values_only=True)); book.close()
        assert any(r[0] == 'crop_data' and r[1] == 'grain' and r[6] == 't ha-1 yr-1' for r in metadata)
        vocab = {f: {r['factor_level_name'] for r in csv.DictReader(io.StringIO(z.read(f + '_factor_data.csv').decode('utf-8-sig')))} for f in FACTORS}
        records = list(csv.DictReader(io.StringIO(z.read('crop_data.csv').decode('utf-8-sig'))))
    predictions = {}
    for row in records:
        year = int(row['harvest_year'])
        splits = [s for s in ('training', 'evaluation') if plan['split'][s][0] <= year <= plan['split'][s][1]]
        if not splits: continue
        if len(splits) != 1: raise ValueError('Overlapping planned periods')
        plot = plot_id(row['plot']); subplot = row['sub_plot'].strip().lower()
        subplot = '' if subplot in ('*', '') else subplot
        key = (year, plot, subplot)
        if key in seen: raise ValueError('Duplicate plot/year/subplot')
        seen.add(key)
        if any(row[f + '_factor_level'] not in vocab[f] for f in FACTORS): raise ValueError('Unknown treatment factor')
        stratum = treatment(row)
        try:
            grain, area = float(row['grain']), float(row['area_ha'])
            sowing, harvest = date.fromisoformat(row['sow_date']), date.fromisoformat(row['harvest_date'])
        except ValueError:
            excluded['missing_yield_area_or_dates'] += 1; continue
        if not math.isfinite(grain) or grain < 0 or not math.isfinite(area) or area <= 0 or sowing >= harvest or harvest.year != year:
            excluded['invalid_yield_area_or_dates'] += 1; continue
        if year not in predictions: predictions[year] = capacity(year, weather)
        if predictions[year] is None:
            excluded['invalid_crop_year_weather'] += 1; continue
        groups[year, stratum].append(dict(grain=grain, area=area, plot=plot, subplot=subplot,
            sow_date=sowing.isoformat(), harvest_date=harvest.isoformat(), cultivar=row['cultivar'],
            calendar=observed_calendar(sowing, harvest, year, weather), note=row['note']))
    cases = []
    for (year, stratum), rows in sorted(groups.items()):
        if stratum == 'unmanured_plot3' and len({(r['sow_date'], r['harvest_date'], r['cultivar']) for r in rows}) != 1:
            raise ValueError('Conflicting primary agronomy')
        area = sum(r['area'] for r in rows)
        cases.append(dict(case_id=f'ERA:Broadbalk:{year}:{stratum}', site_id='ERA:Broadbalk', year=year,
            split='training' if year <= plan['split']['training'][1] else 'evaluation', stratum=stratum,
            observed_t_ha=sum(r['grain'] * r['area'] for r in rows) / area, area_ha=area,
            source_records=rows, **predictions[year]))
    assert_temporal_integrity(cases, plan)
    return cases, dict(excluded)


def primary(cases, split):
    return [c for c in cases if c['split'] == split and c['stratum'] == 'unmanured_plot3']


def metrics(cases, scale, training_mean):
    if not cases: return dict(n=0)
    y = np.array([c['observed_t_ha'] for c in cases])
    p = np.array([c['baseline_t_ha'] * scale for c in cases])
    error = np.abs(np.log10(np.maximum(y, FLOOR) / np.maximum(p, FLOOR)))
    rmse = float(np.sqrt(np.mean((p-y)**2)))
    reference = float(np.sqrt(np.mean((training_mean-y)**2)))
    correlation = float(np.corrcoef(p, y)[0, 1]) if np.ptp(p) > 1e-12 and np.ptp(y) > 1e-12 else None
    return dict(n=len(cases), MAE_log10=float(error.mean()), MAE_t_ha=float(np.mean(abs(p-y))),
        RMSE_t_ha=rmse, Pearson_r=correlation, RMSE_skill_vs_training_mean=1-rmse/reference if reference > 0 else None,
        observed_mean=float(y.mean()), predicted_mean=float(p.mean()), fraction_within_factor2=float(np.mean(error <= np.log10(2))))


def select(cases, plan):
    train = primary(cases, 'training')
    if len(train) < plan['eligibility']['minimum_training_years']: raise ValueError('Insufficient primary training years')
    reference = float(np.mean([c['observed_t_ha'] for c in train]))
    grid = plan['model']['scale_grid']
    scales = np.geomspace(grid['minimum'], grid['maximum'], grid['count'])
    scale = float(min(scales, key=lambda s: (metrics(train, s, reference)['MAE_log10'], abs(math.log(s)), s)))
    return dict(scale=scale, training_mean_t_ha=reference, baseline=metrics(train, 1., reference),
                candidate=metrics(train, scale, reference), candidate_count=len(scales),
                training_case_ids=[c['case_id'] for c in train], evaluation_targets_scored=False)
