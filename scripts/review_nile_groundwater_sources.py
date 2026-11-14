"""Independent source parsing and Decimal checks; producer is not imported."""
import csv
from decimal import Decimal,localcontext
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/nile_groundwater_sources_20261114'
CACHE=ROOT/'data/cache/nile_groundwater_sources_20261114'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Shell(HTMLParser):
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='input' and a.get('id')=='article_metaJson':self.meta=json.loads(a['value'])


class Table(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag=='td':self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=='td':self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row)


def read_csv(name):
    with (OUT/name).open() as file:return list(csv.DictReader(file))


def main():
    r=json.loads((OUT/'reference.json').read_text())
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    for row in r['sources']:
        assert sha(CACHE/row['file'])==row['sha256']
        if 'repository_snapshot' in row:assert sha(ROOT/row['repository_snapshot'])==row['sha256']
    shell=Shell();shell.feed((CACHE/'sakha2023.html').read_text());tables={}
    xml=ET.fromstring((CACHE/'sakha2023.xml').read_bytes())
    for key in ['T1','T2']:
        p=Table();p.feed(next(t['table'] for t in shell.meta['tabList'] if t['id']==key));tables[key]=p.rows
        direct=xml.find('.//table-wrap[@id="'+key+'"]/table/tbody')
        other=[[' '.join(''.join(c.itertext()).split()) for c in row] for row in direct]
        assert p.rows==other,key
    months=['November','December','January','February','March','April','May','June','July','August']
    sites=['El-Baghour','Berket El-Saba','Talla','Shebin El-Kom'];expected=[]
    with pdfplumber.open(CACHE/'amer2019.pdf') as pdf:
        assert len(pdf.pages)==14
        page=pdf.pages[10];words=page.extract_words();pdf_cells=0
        for month in months:
            word=next(w for w in words if w['text'].endswith(month))
            row=sorted([w for w in words if abs(w['top']-word['top'])<2 and w['x0']>word['x1']],key=lambda w:w['x0'])
            values=[w['text'] for w in row];assert len(values)==8,(month,values)
            for i,site in enumerate(sites):expected.append((month,2014 if month in months[:2] else 2015,site,int(values[2*i]),values[2*i+1]));pdf_cells+=2
        context=' '.join(re.sub(r'-\s*\n\s*','',pdf.pages[6].extract_text()+pdf.pages[9].extract_text()).split()).lower()
        assert 'furrow irrigation' in context and 'piezometers' in context and 'before and after direct irrigation' in context
        assert 'estimated empirically' in context and 'calculated' in context
    actual=read_csv('water_tables.csv');assert len(actual)==40
    assert [(a['month'],int(a['year']),a['site'],int(a['depth_cm']),a['fitted_m_text']) for a in actual]==expected
    soil=read_csv('sakha_soils.csv');assert len(soil)==3
    keys=['bulk_density_g_cm3','ph','ec_ds_m','sar_printed','ksat_m_h_printed','clay_pct','silt_pct','sand_pct']
    soil_cells=0
    for saved,source in zip(soil,tables['T1']):
        assert saved['layer_cm']==source[0] and saved['texture']==source[-1]
        for key,value in zip(keys,source[1:9]):assert Decimal(saved[key])==Decimal(value);soil_cells+=1
        assert sum(Decimal(source[i]) for i in [6,7,8])==100
    checks=read_csv('sakha_flux_checks.csv');assert len(checks)==4
    maxerror=0.;discrepancies=[]
    with localcontext() as ctx:
        ctx.prec=50
        for i,a in enumerate(checks):
            uptake=Decimal(tables['T2'][0][i+1]);percent=Decimal(tables['T2'][1][i+1]);et=Decimal(['396.7','385.3'][i%2])
            ratio=100*uptake/et;difference=ratio-percent
            assert Decimal(a['inferred_uptake_mm'])==uptake and Decimal(a['table_percent'])==percent and Decimal(a['section_3_3_et_mm'])==et
            maxerror=max(maxerror,abs(float(ratio)-float(a['computed_percent'])),abs(float(difference)-float(a['computed_minus_printed_pct_points'])))
            assert abs(float(ratio)-float(a['computed_percent']))<1e-12 and abs(float(difference)-float(a['computed_minus_printed_pct_points']))<1e-12
            assert abs(difference)>.05 and a['consistent_with_0_1pct_rounding']=='False'
            discrepancies.append(dict(treatment=a['treatment'],season=int(a['season']),source_percent=str(percent),uptake_over_stated_et_percent=str(ratio)))
    text=' '.join(' '.join(xml.itertext()).split())
    for term in ['time-domain reflectometry','same actual-evapotranspiration','396.7 and 385.3','105.7 and 40.5','26.4% and 10.1%','0.4 and 0.8 m','measured directly before irrigation']:assert term in text,term
    assert '39.98%' in text and '21.70%' in text and not r['facts']['sakha2023']['soil_water']['storage_mm_computed']
    assert not r['earth_fields_scored'] and not r['adopt']
    fresh={}
    for name in ['reference.json','water_tables.csv','sakha_soils.csv','sakha_flux_checks.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),reference_sha256=sha(OUT/'reference.json'),method='Producer not imported. PDFplumber word geometry vs pdftotext; stdlib HTMLParser/ElementTree vs lxml for all selected table rows; 50-digit Decimal dimensional/percentage checks. Published inconsistencies retained, not repaired.',water_table_rows=40,pdf_numeric_cells=pdf_cells,soil_numeric_cells=soil_cells,inferred_flux_rows=4,all_four_percentages_fail_stated_ET_rounding=True,percentage_discrepancies=discrepancies,max_float_vs_decimal_pct_error=maxerror,soil_storage_mm_derived=False,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),earth_fields_scored=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Reviewed80PDF cells,24soil cells and all four inconsistent percentage rows;four fresh exports exact')


if __name__=='__main__':main()
