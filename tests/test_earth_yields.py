"""Scientific identity, unit and chronology guards for historical yield tests."""
import math

import numpy as np
import openpyxl
import pytest

from harvest.earth_yields import (FACTORS, assert_temporal_integrity, calendar_keys,
    capacity, load_weather, metrics, observed_calendar, plot_id, treatment)
from datetime import date


def constant_weather(first=1878, last=1902):
    return {(y, m): dict(T=15., Tmax=20., Tmin=10., P=100., PET=40., soil_start=100.,
        valid=True, rain_missing_days=0, temperature_missing_days=0) for y in range(first, last + 1) for m in range(1, 13)}


def test_previous_autumn_not_future_and_no_cyclic_season():
    weather = constant_weather()
    result = capacity(1901, weather)
    assert result['baseline_t_ha'] == pytest.approx(1.)  # gross harvested, before seed/milling
    assert result['crop_year_start'] == [1900, 9]
    assert result['crop_year_end'] == [1901, 8]
    for m in range(9, 13): weather[1901, m]['T'] = -100.
    assert capacity(1901, weather) == result  # future autumn not recycled into sowing
    for m in range(9, 13): weather[1900, m]['valid'] = False
    assert capacity(1901, weather) is None


def test_calendar_dormancy_failure_not_repaired_by_scale():
    weather = constant_weather()
    weather[1901, 1]['T'] = 1.
    result = observed_calendar(date(1900, 10, 20), date(1901, 8, 15), 1901, weather)
    assert result['months'] == 11
    assert set(result['failures']) == {'length', 'temperature'}
    assert result['representable'] is False
    assert calendar_keys(date(1900, 12, 20), date(1901, 2, 15)) == [(1900, 12), (1901, 1), (1901, 2)]


def test_canonical_plot_and_strict_input_separation():
    assert plot_id('03.0') == '3'
    assert plot_id('2.10') == '2.1'
    row = dict(plot='3', **{f + '_factor_level': 'nil' for f in FACTORS})
    assert treatment(row) == 'unmanured_plot3'
    row['n_factor_level'] = 'N1'
    with pytest.raises(ValueError, match='not all-nil'): treatment(row)
    row['plot'] = '7'
    assert treatment(row) == 'mineral_only'
    row['fym_factor_level'] = 'FYM'
    assert treatment(row) == 'other_organic_or_mixed'
    row['n_factor_level'] = 'nil'
    assert treatment(row) == 'fym_only'


def test_temporal_guard_allows_same_site_but_rejects_fold_errors():
    plan = dict(split=dict(training=[1879, 1900], evaluation=[1901, 1925]))
    cases = [dict(year=y, site_id='ERA:Broadbalk', stratum='unmanured_plot3', split=s) for y, s in [(1900, 'training'), (1901, 'evaluation')]]
    assert_temporal_integrity(cases, plan)
    with pytest.raises(ValueError, match='Duplicate'): assert_temporal_integrity(cases + cases[:1], plan)
    cases[-1]['split'] = 'training'
    with pytest.raises(ValueError, match='split mismatch'): assert_temporal_integrity(cases, plan)


def test_yield_improvement_does_not_imply_interannual_skill():
    cases = [dict(observed_t_ha=y, baseline_t_ha=1.) for y in [.5, 1., 1.5]]
    result = metrics(cases, 1., 1.)
    assert result['Pearson_r'] is None
    assert result['RMSE_skill_vs_training_mean'] == pytest.approx(0.)
    assert math.isfinite(metrics([dict(observed_t_ha=0., baseline_t_ha=0.)], 1., .5)['MAE_log10'])


def test_temperature_import_uses_means_not_monthly_extremes(tmp_path):
    """Extreme-block DTR would greatly inflate Hargreaves ET; make it distinct."""
    book = openpyxl.Workbook(); book.remove(book.active)
    for name, col, label, mean in [('Tmean', 18, 'Mean Temperature (Mean)', 10.), ('Tmax', 18, 'Maximum Temperature (Mean)', 15.), ('Tmin', 19, 'Minimum Temperature (Mean)', 5.)]:
        sheet = book.create_sheet(name)
        sheet.cell(1, col, label); sheet.cell(2, col + 1, 'Jan'); sheet.cell(3, 1, 1878)
        for m in range(12):
            sheet.cell(3, m + 2, 99.)
            sheet.cell(3, col + m + 1, mean)
    counts = book.create_sheet('DAYS'); counts.cell(4, 2, 1878)
    from calendar import monthrange
    for m in range(1, 13): counts.cell(4, m + 2, monthrange(1878, m)[1])
    book.save(tmp_path / 'roth_temperature_0.xlsx')
    book = openpyxl.Workbook(); data = book.active; data.title = 'DATA'; data.cell(5, 1, 1878)
    counts = book.create_sheet('DAYS'); counts.cell(4, 2, 1878)
    for m in range(1, 13):
        data.cell(5, m + 1, 80.); counts.cell(4, m + 2, monthrange(1878, m)[1])
    book.save(tmp_path / 'roth_rain_0.xlsx')
    weather = load_weather(tmp_path, 1878, 51.81)
    assert weather[1878, 1]['T'] == 10.
    assert weather[1878, 1]['Tmax'] - weather[1878, 1]['Tmin'] == 10.
    assert all(r['valid'] for r in weather.values())
    assert 0 < weather[1878, 7]['PET'] < 200
    book = openpyxl.load_workbook(tmp_path / 'roth_temperature_0.xlsx')
    book['DAYS'].cell(4, 3, 30)  # one missing January reading: flagged, eligible
    book['DAYS'].cell(4, 4, 26)  # two missing February readings: ineligible
    book.save(tmp_path / 'roth_temperature_0.xlsx')
    weather = load_weather(tmp_path, 1878, 51.81)
    assert weather[1878, 1]['valid'] and weather[1878, 1]['temperature_missing_days'] == 1
    assert not weather[1878, 2]['valid']
