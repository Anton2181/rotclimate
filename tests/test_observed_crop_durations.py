from scripts.check_observed_crop_durations import duration_distance,score_records


def record(**changes):
    row={'Data.ID':'1','Crop':'Wheat','Plant.median':'300','Harvest.median':'150','tot.days':'215',
         'Qualifier':'Winter','Location':'Example','Level':'N','Source':'fixture',
         'ndays.growing.season.below.0':'NA'}
    row.update(changes);return row


PLAN={'crop_map':{'Wheat':'wheat'},'model_duration_days':{'wheat':[120,270]}}


def test_duration_envelope_does_not_treat_interior_dates_as_exact_bin_prediction():
    assert duration_distance(215,120,270)==0
    assert duration_distance(300,120,270)==30
    assert duration_distance(100,120,270)==20


def test_wrapping_winter_dates_remain_valid_and_missing_cold_is_not_zero():
    rows,excluded=score_records([record()],PLAN)
    assert not excluded and rows[0]['qualifier']=='Winter'
    assert rows[0]['climate_days_below_zero_in_season'] is None
    assert rows[0]['circular_date_duration_difference']==0


def test_duplicate_observations_and_unmapped_crops_are_retained_as_exclusions():
    rows,excluded=score_records([record(),record(),record(**{'Data.ID':'2','Crop':'Millet'})],PLAN)
    assert not rows
    assert [r['reason'] for r in excluded]==['missing_or_duplicate_id','missing_or_duplicate_id','unmapped_crop']


def test_source_exclude_qualifier_is_preserved_and_flagged_instead_of_pooled():
    rows,excluded=score_records([record(Qualifier='Winter.Exclude')],PLAN)
    assert not excluded and rows[0]['source_flagged_exclude']
    assert rows[0]['qualifier']=='Winter.Exclude'
