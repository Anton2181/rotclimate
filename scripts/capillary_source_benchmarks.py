"""Extract hydraulic source contexts and compare the declared FAO61 example."""
import argparse
import csv
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.capillary_hydraulics import HydraulicSoil,stationary_profile_cm
from qualify_flood_storage_sources import Rows
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/capillary_hydraulics_20261114/plan.json'
CACHE=ROOT/'data/cache/recession_groundwater_20261114'
OUT=ROOT/'output/capillary_hydraulics_20261114'
FLUXES=[10.,7.5,5.,2.5,1.,0.]


def parses(raw):
    parser=Rows();parser.feed(raw)
    second=[]
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw,re.S|re.I):
        second.append([' '.join(unescape(re.sub(r'<[^>]*>','',v)).split()) for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S|re.I)])
    return parser.rows,second


def soil_rows(rows):
    result=[]
    for row in rows:
        if len(row)!=7 or not re.fullmatch('[BO][0-9]+',row[0]):continue
        try:values=[float(v.replace(' ','')) for v in row[1:]]
        except ValueError:continue
        result.append(dict(code=row[0],**dict(zip(['theta_residual','theta_saturated','ksat_cm_day','alpha_cm_inv','connectivity','n'],values)),source_cells=row))
    assert len(result)==28 and len({v['code'] for v in result})==28
    return result


def profile_rows(raw):
    a=raw.index('TABLE A5.5');b=raw.index('</TABLE>',a)
    first,second=parses(raw[a:b+8])
    choose=lambda rows:[v for v in rows if len(v)==9 and re.fullmatch(r'-?\d+',v[0])]
    result=choose(first);assert result==choose(second) and len(result)==41
    assert [int(v[0]) for v in result]==list(range(0,-401,-10))
    return result


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());CACHE.mkdir(parents=True,exist_ok=True)
    for name,source in plan['sources'].items():
        path=CACHE/name;prior=ROOT/'data/cache/flood_storage_sources_20261114'/name
        if not path.exists() and prior.exists():shutil.copyfile(prior,path)
        if not path.exists():
            request=urllib.request.Request(source['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=60) as response:data=response.read()
            assert __import__('hashlib').sha256(data).hexdigest()==source['sha256'],'Source changed; audit before use'
            path.write_bytes(data)
        assert sha(path)==source['sha256'],name
        if name.endswith('.pdf'):assert path.read_bytes().startswith(b'%PDF-'),name
    tests=['capillary_hydraulics','reference_forcing','reference_eto','crop_stage','rain_timing','river_fields','field_clock','soil_drying','flood_storage','flood_water','flood_timing','flood_gauge_quality']
    controls=subprocess.run([sys.executable,'-m','pytest','-q',*[f'tests/test_{name}.py' for name in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    if out.resolve()==OUT.resolve():
        out.mkdir(parents=True,exist_ok=True)
        write(OUT/'controls.json',dict(status='passed_before_component_outputs',producer_sha256=sha(Path(__file__)),stdout=controls.stdout))
    assert (OUT/'controls.json').exists(),'Run canonical preflight before fresh exports'
    raw=(CACHE/'fao61_annex5.html').read_text(encoding='latin1');first,second=parses(raw)
    soils=soil_rows(first);assert soils==soil_rows(second)
    rows=profile_rows(raw);target=next(v for v in soils if v['code']=='O8')
    parameters={key:value for key,value in target.items() if key not in ['code','source_cells']}
    assert list(parameters.values())==[0.,.47,9.08,.0136,-.803,1.342]
    soil=HydraulicSoil(**parameters);heads=-np.array([float(v[0]) for v in rows])
    profiles=stationary_profile_cm(soil,heads,np.array(FLUXES));benchmarks=[]
    for i,row in enumerate(rows):
        for j,flux in enumerate(FLUXES):
            text=row[3+j];printed=float(text);decimals=len(text.split('.')[1]) if '.' in text else 0
            tolerance=.5*10**(-decimals) if '.' in text else 0.
            value=float(profiles[j,i]);error=value-printed
            benchmarks.append(dict(flux_mm_day=flux,suction_cm=heads[i],source_z_text=text,source_z_cm=printed,model_z_cm=value,tolerance_cm=tolerance,within_rounding=int(abs(error)<=tolerance+1e-9),error_cm=error))
    pdf=subprocess.run(['pdftotext','-layout',str(CACHE/'butzer1976.pdf'),'-'],capture_output=True,text=True,check=True).stdout.split('\f')
    assert 'capillary soil moisture' in pdf[34] and 'Omo floodplain' in pdf[34]
    assert 'summer water table' in pdf[105] and '3-4 m below the surface' in pdf[105]
    historic=dict(butzer1976_p19=dict(pdf_page=35,interpretation='Uses Omo/Senegal/Chari-Logone floodplain analogies for prehistoric Nile ecology; not observations of Roman Nile capillary flux'),butzer1976_p90=dict(pdf_page=106,interpretation='Most areas described with summer water table at least3–4m below surface; this is not a winter depth'),butzer1984_p105=dict(pdf_page=4,interpretation='Traditional post-flood season described with high water table; no local quantitative recharge/storage/flux inferred'),fao56_ch8=dict(interpretation='Capillary contribution depends on soil, water table and root wetness; approximate1m-below-root convention is not a universal hydraulic cutoff'),fao61=dict(interpretation='Steady unsaturated flow and Dutch soil hydraulic profiles support a generic mathematical check, not Nile hydraulic parameter adoption'))
    base=ROOT/'output/regional_reference_forcing_20261114';prior=json.loads((base/'results.json').read_text());protected=dict(prior['unchanged_sha256'])
    for receipt in ['weather_review.json','review.json']:
        old=json.loads((base/receipt).read_text())
        for name,digest in old['fresh_byte_exact'].items():protected[str((base/name).relative_to(ROOT))]=digest
        protected[str((base/receipt).relative_to(ROOT))]=sha(base/receipt)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    out.mkdir(parents=True,exist_ok=True)
    with (out/'benchmarks.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(benchmarks[0]));writer.writeheader();writer.writerows(benchmarks)
    function_rows=[]
    for source_soil in soils:
        model=HydraulicSoil(**{key:value for key,value in source_soil.items() if key not in ['code','source_cells']})
        for h in [0.,1.,5.,10.,15.,20.,31.,50.,100.,250.,500.,1000.,2500.,5000.,10000.,16000.]:
            function_rows.append(dict(soil=source_soil['code'],suction_cm=h,water_content_cm3_cm3=float(model.water_content(h)),conductivity_cm_day=float(model.conductivity_cm_day(h))))
    with (out/'hydraulic_functions.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(function_rows[0]));writer.writeheader();writer.writerows(function_rows)
    paths=[Path(__file__),ROOT/'harvest/capillary_hydraulics.py',ROOT/'tests/test_capillary_hydraulics.py',ROOT/'scripts/qualify_flood_storage_sources.py',PLAN]
    write(out/'reference.json',dict(status='source_qualified_stationary_component_only',sources=plan['sources'],soil_parameters_table_a5_4=soils,worked_soil='O8',fluxes_mm_day=FLUXES,source_profile_table_a5_5=rows,published_z_cells=len(benchmarks),within_printed_rounding=sum(v['within_rounding'] for v in benchmarks),max_published_z_error_cm=max(abs(v['error_cm']) for v in benchmarks),hydraulic_function_rows=len(function_rows),historical_context=historic,controls_sha256=sha(OUT/'controls.json'),producers={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256={name:sha(out/name) for name in ['benchmarks.csv','hydraulic_functions.csv']},unchanged_sha256=protected,water_supplied_mm=0,regional_fields_scored=False,adopt=False))
    print(controls.stdout.strip());print('Parsed28profiles;published z rounding agreement',sum(v['within_rounding'] for v in benchmarks),'/',len(benchmarks),'max error cm',max(abs(v['error_cm']) for v in benchmarks))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
