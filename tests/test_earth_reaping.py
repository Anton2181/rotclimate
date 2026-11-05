import math
import numpy as np
from harvest.earth_reaping import identifier,number,district_split,select_scale,metrics


def case(id,district,ratio,split='training'):
    return dict(case_id=id,district_id=district,split=split,baseline_hours=48.,human_reaping_hours=48.*ratio)


def test_source_identifiers_and_missing_numbers_are_not_silent_zero():
    assert identifier('00123.0')=='123' and identifier('A/a')=='A/A'
    assert number('') is None and number('nan') is None and number('bad') is None
    assert number('0')==0


def test_district_split_keeps_panel_together():
    plan=dict(split=dict(training_below=.7))
    a=district_split('east|STATE|DISTRICT',plan)
    assert a==district_split('east|STATE|DISTRICT',plan)
    assert a in ['training','evaluation']


def test_selection_cannot_read_evaluation_targets():
    train=[case('1','A',2),case('2','B',2),case('3','C',2)]
    a=select_scale(train+[case('4','D',.01,'evaluation')],[.25,4])
    b=select_scale(train+[case('4','D',100000,'evaluation')],[.25,4])
    assert a==b==2


def test_each_district_has_equal_weight_not_each_household():
    rows=[case(str(i),'A',.5) for i in range(100)]+[case('b','B',2),case('c','C',3)]
    assert select_scale(rows,[.25,4])==2


def test_closed_form_scale_is_global_l1_minimum_with_bounds():
    rows=[case('1','A',.1),case('2','B',2),case('3','C',10)]
    optimum=select_scale(rows,[.25,4]);best=metrics(rows,optimum)['equal_district_abs_log10_error']
    assert all(metrics(rows,float(s))['equal_district_abs_log10_error']>=best-1e-12 for s in np.geomspace(.25,4,501))
    assert select_scale([case('1','A',20)],[.25,4])==4


def survey_fixture(tmp_path,monkeypatch,extra_rows=(),extra_crops=()):
    import csv,io,json,zipfile
    import harvest.earth_reaping as module
    from pathlib import Path
    plan=json.loads((Path(__file__).resolve().parents[1]/'calibration/earth_components_20261105/plan.json').read_text())
    general=dict(vdsid_hhid='11',sur_yr=2010,family_size=4,state='State',district='District',village='Village')
    crop=dict(vdsid_hhid='11',sur_yr=2010,plot_code='A1',season='Rabi',crop_name='Wheat',prct_area=100,plot_area=1,irri_area=0,op_main_prod_unit='Kg',op_main_prod_qty=1000)
    events=[dict(Vdsid_hhid='11',Sur_yr=2010,Plot_code='A1',Season='Rabi',Operation='Harvesting',Lab_type=lab,Work_hr=h,Round_no=1,Dt_oper='1/1/2010',Type_mat='') for lab,h in [('FM',50),('HF',20),('OB',1000)]]
    monkeypatch.setattr(module,'rows_xlsx',lambda z,m:iter([general] if 'General Information' in m else [crop,*extra_crops]))
    with zipfile.ZipFile(tmp_path/'General Endowments Schedule.zip','w') as z:z.writestr('Data on General Information of SAT India.xlsx','placeholder')
    with zipfile.ZipFile(tmp_path/'Cultivation.zip','w') as z:
        z.writestr('Data on Cropping Pattern and Output of SAT India.xlsx','placeholder')
        f=io.StringIO();writer=csv.DictWriter(f,fieldnames=events[0].keys());writer.writeheader();writer.writerows([*events,*extra_rows]);z.writestr('Data on Cultivation Input Details of SAT India.csv',f.getvalue())
    return module.prepare(tmp_path,plan)


def test_observed_area_population_and_human_hours_are_independent(tmp_path,monkeypatch):
    rows,excluded,_=survey_fixture(tmp_path,monkeypatch)
    assert not excluded and len(rows)==1
    r=rows[0]
    assert r['household_members']==4 and r['hectares']==.40468564224
    assert r['human_reaping_hours']==70 and r['family_reaping_hours']==50
    assert r['hired_reaping_hours']==20 and r['strict_recorded_input_subgroup']
    assert r['grain_kg']==1000 and 'vdsid_hhid' not in r


def test_ambiguous_duplicate_work_event_is_not_double_counted(tmp_path,monkeypatch):
    extra=dict(Vdsid_hhid='11',Sur_yr=2010,Plot_code='A1',Season='Rabi',Operation='Harvesting',Lab_type='FM',Work_hr=50,Round_no=1,Dt_oper='1/1/2010',Type_mat='')
    rows,excluded,_=survey_fixture(tmp_path,monkeypatch,[extra])
    assert rows==[] and excluded['ambiguous_event']==1


def test_bundled_tasks_are_not_relabelled_as_reaping(tmp_path,monkeypatch):
    extra=dict(Vdsid_hhid='11',Sur_yr=2010,Plot_code='A1',Season='Rabi',Operation='Harvesting & Threshing',Lab_type='FM',Work_hr=50,Round_no=1,Dt_oper='1/1/2010',Type_mat='')
    rows,excluded,_=survey_fixture(tmp_path,monkeypatch,[extra])
    assert rows==[] and excluded['bundled_task']==1


def test_recorded_harvest_machinery_prevents_manual_task_comparison(tmp_path,monkeypatch):
    extra=dict(Vdsid_hhid='11',Sur_yr=2010,Plot_code='A1',Season='Rabi',Operation='Harvesting',Lab_type='',Work_hr='',Round_no=1,Dt_oper='1/1/2010',Type_mat='Machinery')
    rows,excluded,_=survey_fixture(tmp_path,monkeypatch,[extra])
    assert rows==[] and excluded['machinery_harvest']==1


def test_whole_plot_code_keeps_subplots_separate(tmp_path,monkeypatch):
    crop=dict(vdsid_hhid='11',sur_yr=2010,plot_code='A2',season='Rabi',crop_name='Wheat',prct_area=100,plot_area=2,irri_area=0,op_main_prod_unit='Kg',op_main_prod_qty=2000)
    extra=dict(Vdsid_hhid='11',Sur_yr=2010,Plot_code='A2',Season='Rabi',Operation='Harvesting',Lab_type='FM',Work_hr=40,Round_no=1,Dt_oper='1/1/2010',Type_mat='')
    rows,excluded,_=survey_fixture(tmp_path,monkeypatch,[extra],[crop])
    assert len(rows)==2 and sorted(r['human_reaping_hours'] for r in rows)==[40,70]
