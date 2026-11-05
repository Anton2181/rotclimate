"""Independent plot/household evidence for a narrowly defined manual task.

Raw public survey files remain in cache. No respondent names are retained.
This modern comparator cannot authorize ancient-model default changes.
"""
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
import csv
import hashlib
import io
import json
import math
import re
import zipfile
import numpy as np

ACRE_HA=.40468564224
BASE_REAPING={'WHEAT':48.,'BARLEY':32.}


def text(value):return ' '.join(str(value or '').strip().upper().split())


def identifier(value):
    s=str(value or '').strip()
    try:
        d=Decimal(s)
        if d.is_finite() and d==d.to_integral_value():return str(int(d))
    except InvalidOperation:pass
    return text(s)


def number(value):
    try:n=float(str(value).strip())
    except (ValueError,TypeError):return None
    return n if math.isfinite(n) else None


def district_split(district,plan):
    digest=hashlib.sha256(('rotclimate-vdsa-reaping-v1|'+district).encode()).hexdigest()
    return 'training' if int(digest[:8],16)/2**32<plan['split']['training_below'] else 'evaluation'


def safe_id(value):return hashlib.sha256(('rotclimate-vdsa-public-v1|'+value).encode()).hexdigest()[:20]


def rows_xlsx(archive,member):
    import openpyxl
    wb=openpyxl.load_workbook(io.BytesIO(archive.read(member)),read_only=True,data_only=True)
    try:
        iterator=wb.active.iter_rows(values_only=True);header=[text(v).lower() for v in next(iterator)]
        for row in iterator:
            if row and any(v is not None for v in row):yield dict(zip(header,row))
    finally:wb.close()


def key(region,row):return (region,identifier(row.get('vdsid_hhid')),identifier(row.get('sur_yr')),text(row.get('plot_code')),text(row.get('season')))


def prepare(cache,plan):
    cache=__import__('pathlib').Path(cache);years=set(map(str,plan['data_rules']['years']));metadata=defaultdict(set);exclusions=Counter();source_counts={}
    with zipfile.ZipFile(cache/'General Endowments Schedule.zip') as z:
        for member in z.namelist():
            if 'General Information' not in member:continue
            region='east' if 'East India' in member else 'sat'
            for row in rows_xlsx(z,member):
                year=identifier(row.get('sur_yr'))
                if year not in years:continue
                n=number(row.get('family_size'));state=text(row.get('state'));district=text(row.get('district'));village=text(row.get('village'))
                if n is None or n<=0 or n!=int(n) or not state or not district or not village:continue
                metadata[region,identifier(row.get('vdsid_hhid')),year].add((int(n),state,district,village))
    crops=defaultdict(list)
    with zipfile.ZipFile(cache/'Cultivation.zip') as z:
        for member in z.namelist():
            if not member.endswith('.xlsx'):continue
            region='east' if 'East India' in member else 'sat';count=0
            for row in rows_xlsx(z,member):
                k=key(region,row)
                if k[2] in years:crops[k].append(row);count+=1
            source_counts[member]=count
        candidates={}
        for k,group in crops.items():
            if not any(text(r.get('crop_name')) in BASE_REAPING for r in group):continue
            if len(group)!=1:exclusions['ambiguous_or_mixed_crop_key']+=1;continue
            row=group[0];crop=text(row.get('crop_name'));share=number(row.get('prct_area'));area=number(row.get('plot_area'))
            if share is None or abs(share-100)>1e-6:exclusions['not_documented_sole_crop']+=1;continue
            if area is None or area<=0 or not k[3] or not k[4]:exclusions['invalid_area_or_plot_season']+=1;continue
            meta=metadata.get(k[:3],set())
            if len(meta)!=1:exclusions['missing_or_ambiguous_household_metadata']+=1;continue
            members,state,district,village=next(iter(meta));d='|'.join([k[0],state,district]);qid=safe_id('|'.join(k));unit=text(row.get('op_main_prod_unit'));qty=number(row.get('op_main_prod_qty'));conversion={'KG':1.,'QT':100.}.get(unit)
            grain=qty*conversion if qty is not None and qty>=0 and conversion else None
            candidates[k]=dict(case_id=qid,household_id=safe_id('|'.join(k[:2])),survey_year=int(k[2]),source_region=k[0],district_id=safe_id(d),village_id=safe_id(d+'|'+village),split=district_split(d,plan),crop=crop,hectares=area*ACRE_HA,household_members=members,irrigated_area_acres=number(row.get('irri_area')),grain_kg=grain,
                human_reaping_hours=0.,family_reaping_hours=0.,hired_reaping_hours=0.,exchange_reaping_hours=0.,harvest_events=0,invalid_hours=False,ambiguous_event=False,bundled_task=False,machinery_harvest=False,modern_input=False)
        events=defaultdict(set);human=set(plan['data_rules']['human_labour_codes']);family=set(plan['data_rules']['family_labour_codes']);pattern=re.compile(plan['data_rules']['harvest_operation_regex'])
        for member in z.namelist():
            if not member.endswith('.csv'):continue
            region='east' if 'East India' in member else 'sat';count=0
            raw=z.read(member)
            try:decoded=raw.decode('utf-8-sig')
            except UnicodeDecodeError:decoded=raw.decode('cp1252')
            with io.StringIO(decoded,newline='') as f:
                for original in csv.DictReader(f):
                    row={text(k).lower():v for k,v in original.items()};k=key(region,row)
                    if k not in candidates:continue
                    c=candidates[k];count+=1;op=text(row.get('operation'));lab=text(row.get('lab_type'));mat=text(row.get('type_mat'));harvest=('HARVEST' in op or 'REAP' in op)
                    if mat in {'MACHINERY','FERTILIZER','PESTICIDE/FUNGICIDE','WEEDICIDE'}:c['modern_input']=True
                    if harvest and mat=='MACHINERY':c['machinery_harvest']=True
                    if lab not in human:continue
                    if harvest and not pattern.fullmatch(op):c['bundled_task']=True
                    if not pattern.fullmatch(op):continue
                    hours=number(row.get('work_hr'))
                    if hours is None or hours<0:c['invalid_hours']=True;continue
                    event=(op,text(row.get('round_no')),text(row.get('dt_oper')),lab)
                    if event in events[k]:c['ambiguous_event']=True
                    events[k].add(event);c['harvest_events']+=1;c['human_reaping_hours']+=hours
                    if lab in family:c['family_reaping_hours']+=hours
                    elif lab.startswith('H'):c['hired_reaping_hours']+=hours
                    else:c['exchange_reaping_hours']+=hours
            source_counts[member]=count
    output=[]
    for c in candidates.values():
        reason=next((field for field in ['invalid_hours','ambiguous_event','bundled_task','machinery_harvest'] if c[field]),None)
        if reason:exclusions[reason]+=1;continue
        if c['human_reaping_hours']<=0 or not c['harvest_events']:exclusions['no_positive_exact_task_hours']+=1;continue
        c['strict_recorded_input_subgroup']=c['irrigated_area_acres']==0 and not c['modern_input']
        c['baseline_hours']=c['hectares']*BASE_REAPING[c['crop']]
        c['grain_kg_ha']=c['grain_kg']/c['hectares'] if c['grain_kg'] is not None else None
        c['reaping_hours_ha']=c['human_reaping_hours']/c['hectares']
        output.append(c)
    output.sort(key=lambda c:c['case_id'])
    return output,dict(exclusions),source_counts


def select_scale(cases,bounds):
    """Global L1 optimum for one log-scale parameter; districts weigh equally."""
    train=[c for c in cases if c['split']=='training'];counts=Counter(c['district_id'] for c in train)
    if not train:raise ValueError('Training cases required')
    delta=np.array([math.log10(c['human_reaping_hours']/c['baseline_hours']) for c in train]);weights=np.array([1/counts[c['district_id']] for c in train]);order=np.argsort(delta,kind='stable');delta=delta[order];weights=weights[order]
    median=delta[np.searchsorted(np.cumsum(weights),weights.sum()/2)]
    return float(np.clip(10**median,*bounds))


def metrics(cases,scale):
    if not cases:return None
    groups=defaultdict(list)
    for c in cases:groups[c['district_id']].append(math.log10(scale*c['baseline_hours']/c['human_reaping_hours']))
    errors=[np.asarray(v) for v in groups.values()]
    return dict(cases=len(cases),districts=len(groups),equal_district_abs_log10_error=float(np.mean([np.abs(v).mean() for v in errors])),equal_district_signed_log10_error=float(np.mean([v.mean() for v in errors])),median_log10_bias=float(np.median(np.concatenate(errors))),equal_district_within_factor_two=float(np.mean([(np.abs(v)<=math.log10(2)).mean() for v in errors])),per_district={k:dict(cases=len(v),abs_log10_error=float(np.abs(v).mean()),mean_log10_error=float(np.mean(v))) for k,v in groups.items()})
