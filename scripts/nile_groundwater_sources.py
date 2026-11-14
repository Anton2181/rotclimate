"""Retain modern Nile source measurements separately from inferred fluxes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request

from lxml import etree,html

ROOT=Path(__file__).resolve().parents[1]
CAL=ROOT/'calibration/nile_groundwater_sources_20261114'
CACHE=ROOT/'data/cache/nile_groundwater_sources_20261114'
OUT=ROOT/'output/nile_groundwater_sources_20261114'
MONTHS=['November','December','January','February','March','April','May','June','July','August']
SITES=['El-Baghour','Berket El-Saba','Talla','Shebin El-Kom']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def restore():
    CACHE.mkdir(parents=True,exist_ok=True)
    for row in json.loads((CAL/'sources.json').read_text()):
        if 'repository_snapshot' in row:assert sha(ROOT/row['repository_snapshot'])==row['sha256']
        path=CACHE/row['file']
        if not path.exists():
            snapshot=ROOT/row['repository_snapshot'] if 'repository_snapshot' in row else None
            if snapshot is not None:
                assert sha(snapshot)==row['sha256'];shutil.copyfile(snapshot,path)
            else:
                with urllib.request.urlopen(urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:data=response.read()
                assert hashlib.sha256(data).hexdigest()==row['sha256'],row['file']+' changed source bytes'
                path.write_bytes(data)
        assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],row['file']
    assert (CACHE/'amer2019.pdf').read_bytes().startswith(b'%PDF-')
    assert (CACHE/'sakha2023.xml').read_bytes().startswith(b'<?xml')


def rows(table):
    return [[' '.join(cell.itertext()).strip() for cell in tr] for tr in table.xpath('.//tbody/tr')]


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str((CAL/'plan.json').relative_to(ROOT))],cwd=ROOT)==(CAL/'plan.json').read_bytes()
    restore();out.mkdir(parents=True,exist_ok=True)
    text=subprocess.check_output(['pdftotext','-f','11','-l','11','-layout',str(CACHE/'amer2019.pdf'),'-'],text=True)
    water=[]
    for month in MONTHS:
        match=re.search(r'\b'+month+r'\s+((?:\d+\s+\d+\.\d+\s*){4})',text);assert match,month
        values=match.group(1).split();assert len(values)==8
        for i,site in enumerate(SITES):
            water.append(dict(month=month,year=2014 if month in MONTHS[:2] else 2015,site=site,depth_cm=int(values[2*i]),fitted_m_text=values[2*i+1],depth_status='piezometer measurement; before irrigation',m_status='empirically fitted, not independent observation',source='Amer2019 Table3 printed89/PDF11'))
    shell=html.fromstring((CACHE/'sakha2023.html').read_bytes())
    meta=json.loads(shell.get_element_by_id('article_metaJson').get('value'))
    xml=etree.fromstring((CACHE/'sakha2023.xml').read_bytes())
    tables={t['id']:html.fromstring(t['table']) for t in meta['tabList']}
    for key in ['T1','T2']:
        other=xml.xpath('.//table-wrap[@id="'+key+'"]//table');assert len(other)==1
        assert rows(tables[key])==rows(other[0]),key
    soil=[]
    for row in rows(tables['T1']):
        assert len(row)==10
        soil.append(dict(layer_cm=row[0],bulk_density_g_cm3=float(row[1]),ph=float(row[2]),ec_ds_m=float(row[3]),sar_printed=float(row[4]),ksat_m_h_printed=float(row[5]),clay_pct=float(row[6]),silt_pct=float(row[7]),sand_pct=float(row[8]),texture=row[9]))
    flux=rows(tables['T2']);assert len(flux)==2 and all(len(row)==5 for row in flux)
    checks=[]
    for i,(treatment,season) in enumerate([('CD-0.4',1),('CD-0.4',2),('CD-0.8',1),('CD-0.8',2)]):
        uptake=float(flux[0][i+1]);printed=float(flux[1][i+1]);et=[396.7,385.3][season-1];ratio=100*uptake/et
        checks.append(dict(treatment=treatment,season=season,inferred_uptake_mm=uptake,table_percent=printed,section_3_3_et_mm=et,computed_percent=ratio,computed_minus_printed_pct_points=ratio-printed,consistent_with_0_1pct_rounding=abs(ratio-printed)<=.05,status='inferred residual; not directly measured capillary flux'))
    assert not any(row['consistent_with_0_1pct_rounding'] for row in checks)
    body=' '.join(' '.join(xml.itertext()).split())
    assert all(term in body for term in ['39.98%','21.70%','30.84%','same actual-evapotranspiration','396.7 and 385.3','105.7 and 40.5'])
    facts=dict(
        amer2019=dict(period='November2014–August2015',setting='Furrow-irrigated Menoufia fields plus uncultivated Ebshan profile; modern managed Delta',measured='Piezometer water-table depths, laboratory soil properties and field infiltration',inferred='ETa, crop factor m, hydraulic functions and seasonal capillary contribution are empirical/model-derived',depths='Table3 has four cultivated sites × ten months; monthly depths are not a continuous boundary series',units_flag='Equation1 is a capillary height relation, while printed88 discusses a calculated rise rate; height alone does not determine a rate. No rate adopted.'),
        sakha2023=dict(doi='10.1007/s40333-023-0095-3',setting='Sakha/Motobus,31°15′51″N30°47′06″E; three separately drained0.6ha fields, modern wheat cultivars and fertilizer',periods=['2018-11-15 to2019-04-25','2019-11-20 to2020-04-27'],measured='Flow-meter irrigation, tank/stopwatch drainage, TDR soil water, monthly well depths, roots before irrigation and harvested yields',inferred='Section2.6 estimates groundwater as water-balance residual using ETc; Section3.3 assumes all treatments share control-derived actual ET',soil_water=dict(fc_percent=39.98,wp_percent=21.70,half_depletion_percent=30.84,basis='Percent FC/WP basis and layer assignment are not explicitly identified in the retained methods; TDR is reported for field moisture monitoring',storage_mm_computed=False),source_flags=['Table2 middle percentage cells disagree with Section3.3 prose associations; all table percentages fail uptake/Section3.3-ET arithmetic at0.1% rounding','Equation3 combines water depths in mm with a storage change described as soil-moisture percent; layer/root-depth conversion is not supplied there','Ks header is m/h in both captured table representations; retain as printed without adopting it as a recharge limit'],drainage='Both controlled treatments have actual drains1.2m deep;0.4/0.8m are outlet/weir elevations, not drain burial depths or fixed measured water tables',salinity='Higher salinity under shallow control; two growing seasons do not qualify long-term salinity response'),
        missing=['Consistent local FC/WP basis and layer retention/conductivity profile','Full matched water-table,root development/suction,weather,irrigation/drainage and storage-change time series','Aquifer accessible storage/specific yield, finite recharge boundaries and losses','Historical basin applicability and high-water-table oxygen/salinity/transient constraints'],
        decision='Useful modern measurements/context; insufficient internally consistent inputs for a regional groundwater parameterization. No flux percentage, capacity or local yield adopted.')
    files={'water_tables.csv':water,'sakha_soils.csv':soil,'sakha_flux_checks.csv':checks}
    for name,records in files.items():
        with (out/name).open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    prior=ROOT/'output/paid_groundwater_20261114';r=json.loads((prior/'results.json').read_text());protected=dict(r['unchanged_sha256'])
    for name in ['results.json','demonstrations.csv','synthetic.npz','controls.json','review.json']:protected[str((prior/name).relative_to(ROOT))]=sha(prior/name)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(out/'reference.json',dict(status='modern_local_source_qualification_only',facts=facts,water_table_rows=len(water),soil_layers=len(soil),inferred_flux_rows=len(checks),sources=json.loads((CAL/'sources.json').read_text()),producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),CAL/'plan.json',CAL/'sources.json']},files_sha256={name:sha(out/name) for name in files},unchanged_sha256=protected,earth_fields_scored=False,adopt=False))
    print('Retained40measured depths/fitted factors,three soil layers,four inferred flux rows;no regional groundwater inputs adopted')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
