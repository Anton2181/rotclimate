import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from flood_basin_seasonality import GaugeTable,complete_years


def year(y):return [(f'{y}-{m:02d}-15',str(m)) for m in range(1,13)]


def test_only_complete_calendar_years_in_fixed_window():
    records=year(1900)+year(1901)[:-1]+year(1902)
    years,flow,excluded=complete_years(records,1900,1901)
    assert years==[1900] and flow.tolist()==[list(range(1,13))]
    assert excluded==[dict(year=1901,records=11,reasons=['not_twelve_records'])]


def test_duplicates_qualified_missing_and_negative_values_are_not_filled():
    records=year(1900);records[-1]=records[0]
    assert complete_years(records,1900,1900)[0]==[]
    for bad in ('?12','<1','nan','-2',''):
        records=year(1900);records[2]=('1900-03-15',bad)
        assert complete_years(records,1900,1900)[0]==[]


def test_missing_whole_year_kept_in_exclusion_log():
    years,flow,bad=complete_years([],1900,1901)
    assert years==[] and flow.shape==(0,12) and len(bad)==2


def test_html_table_keeps_source_rows_and_ignores_metadata():
    p=GaugeTable();p.feed('<table><tr><th>Date/Time</th><th>Q</th></tr><tr><td>1900-01-15</td><td>12.0</td></tr><tr><td>1900-02-15</td><td>&lt;1</td></tr></table>')
    assert p.rows==[['1900-01-15','12.0'],['1900-02-15','<1']]
