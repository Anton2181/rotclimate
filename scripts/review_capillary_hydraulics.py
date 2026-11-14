"""Independent source-parser and Decimal review of the stationary component."""
import csv
from decimal import Decimal,localcontext
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/capillary_hydraulics_20261114'
CACHE=ROOT/'data/cache/recession_groundwater_20261114'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceRows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ['td','th'] and self.row is not None:self.cell=[]
    def handle_data(self,value):
        if self.cell is not None:self.cell.append(value)
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None


def properties(parameters,head):
    """Direct source Eq4 powers, independent of the component's log-Se form."""
    residual,saturated,ksat,alpha,connection,n=parameters
    if head==0:return saturated,ksat
    m=1-1/n;x=alpha*head;a=1+x**n
    water=residual+(saturated-residual)/(a**m)
    conductivity=ksat*(a**m-x**(n-1))**2/(a**(m*(connection+2)))
    return water,conductivity


def main():
    r=json.loads((OUT/'reference.json').read_text())
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert sha(OUT/'controls.json')==r['controls_sha256']
    controls=json.loads((OUT/'controls.json').read_text());assert '208 passed' in controls['stdout']
    assert controls['producer_sha256']==sha(ROOT/'scripts/capillary_source_benchmarks.py')
    for name,spec in r['sources'].items():
        assert sha(CACHE/name)==spec['sha256'],name
        if name.endswith('.pdf'):assert (CACHE/name).read_bytes().startswith(b'%PDF-')
    raw=(CACHE/'fao61_annex5.html').read_text(encoding='latin1');parser=SourceRows();parser.feed(raw)
    params={}
    for row in parser.rows:
        if len(row)==7 and re.fullmatch('[BO][0-9]+',row[0]):
            try:values=[Decimal(v.replace(' ','')) for v in row[1:]]
            except Exception:continue
            params[row[0]]=values
    assert len(params)==28
    for soil in r['soil_parameters_table_a5_4']:
        assert [Decimal(v.replace(' ','')) for v in soil['source_cells'][1:]]==params[soil['code']]
        for key,value in zip(['theta_residual','theta_saturated','ksat_cm_day','alpha_cm_inv','connectivity','n'],params[soil['code']]):assert soil[key]==float(value)
    first=raw.index('TABLE A5.5');last=raw.index('</TABLE>',first);p=SourceRows();p.feed(raw[first:last+8])
    source=[row for row in p.rows if len(row)==9 and re.fullmatch(r'-?\d+',row[0])]
    assert source==r['source_profile_table_a5_5'] and len(source)==41
    source_by_head={-Decimal(row[0]):row for row in source}
    maximum_function=0.;function_count=0;max_z=0.;z_count=0;rounding_count=0
    with localcontext() as context:
        context.prec=50
        with (OUT/'hydraulic_functions.csv').open() as file:
            for row in csv.DictReader(file):
                water,k=properties(params[row['soil']],Decimal(row['suction_cm']))
                for key,value in [('water_content_cm3_cm3',water),('conductivity_cm_day',k)]:
                    error=abs(Decimal(row[key])-value);maximum_function=max(maximum_function,float(error))
                    assert error<Decimal('2e-10')
                function_count+=1
        assert function_count==448==r['hydraulic_function_rows']
        expected={}
        for flux in map(lambda value:Decimal(str(value)),r['fluxes_mm_day']):
            value=Decimal(0);expected[(flux,Decimal(0))]=value
            for i in range(1,41):
                h1=Decimal(source[i-1][0]);h2=Decimal(source[i][0])
                _,k=properties(params['O8'],-(h1+h2)/2)
                value+=(h2-h1)/(-1-(flux/10)/k)
                expected[(flux,-h2)]=value
        with (OUT/'benchmarks.csv').open() as file:
            for row in csv.DictReader(file):
                flux,head=Decimal(row['flux_mm_day']),Decimal(row['suction_cm'])
                exact=expected[(flux,head)];error=abs(Decimal(row['model_z_cm'])-exact);max_z=max(max_z,float(error))
                assert error<Decimal('2e-10')
                index=r['fluxes_mm_day'].index(float(flux));text=source_by_head[head][3+index]
                assert row['source_z_text']==text and Decimal(row['source_z_cm'])==Decimal(text)
                tolerance=Decimal('.5')*Decimal(10)**(-len(text.split('.')[1])) if '.' in text else Decimal(0)
                assert Decimal(row['tolerance_cm'])==tolerance
                agrees=abs(exact-Decimal(text))<=tolerance+Decimal('1e-9')
                assert int(row['within_rounding'])==agrees
                assert abs(Decimal(row['error_cm'])-(Decimal(row['model_z_cm'])-Decimal(text)))<Decimal('1e-12')
                rounding_count+=agrees;z_count+=1
        assert z_count==246 and rounding_count==246==r['within_printed_rounding']
    text=subprocess.run(['pdftotext','-layout',str(CACHE/'butzer1976.pdf'),'-'],capture_output=True,text=True,check=True).stdout.split('\f')
    assert 'Omo floodplain' in text[34] and 'capillary soil moisture' in text[34]
    assert 'summer water table' in text[105] and '3-4 m below the surface' in text[105]
    fresh={}
    for name in ['reference.json','benchmarks.csv','hydraulic_functions.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    assert r['water_supplied_mm']==0 and not r['regional_fields_scored'] and not r['adopt']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),reference_sha256=sha(OUT/'reference.json'),method='Independent HTML parameter/profile parsing;50-digit Decimal direct sourceEq4 conductivity and signed-head Eq6 recurrence;component/producer not imported',soil_profiles=28,hydraulic_function_rows=function_count,hydraulic_numeric_cells=2*function_count,max_hydraulic_numeric_error=maximum_function,published_z_cells=z_count,within_printed_rounding=rounding_count,max_profile_numeric_error_cm=max_z,historical_pdf_pages_checked=[35,106],fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),water_supplied_mm=0,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Passed28profiles,896hydraulic cells,246published profile cells and historical context;three fresh numeric files byte-exact')


if __name__=='__main__':main()
