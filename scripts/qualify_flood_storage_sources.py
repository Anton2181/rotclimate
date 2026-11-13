"""Extract generic FAO constraints after the storage sensitivity experiment.

No local soil parameters are fitted and no field model is rerun. Two independent
HTML parsing paths check the small numeric reference tables before publication.
"""
import argparse,hashlib,json,re,urllib.request
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/cache/flood_storage_sources_20261114'
OUT=ROOT/'output/flood_storage_sources_20261114'
SOURCES={
    'fao56_ch7.html':dict(url='https://www.fao.org/4/x0490e/x0490e0c.htm',sha256='81e7f9c06f2cae152bcc0c58b3710f6e4919fefc0d8c5a6404fac917616381b0',locator='FAO56 (Allen et al.1998), Chapter7,Table19 and Equations73–74; soil evaporation layer'),
    'fao56_ch8.html':dict(url='https://www.fao.org/4/x0490e/x0490e0e.htm',sha256='f7eabb739742734c411a8d31527b709fba004a943e373ed406587017b3be0e98',locator='FAO56 (Allen et al.1998), Chapter8,Table22 and Equations82–85; root-zone and daily water balance'),
    'butzer1984.pdf':dict(url='https://sites.utexas.edu/butzer/wp-content/uploads/sites/6106/2017/07/Butzer-1984-LongTermNile.pdf',sha256='689e753dbe637736505f84973c393c56055021a8b9558b4e00ec5b76c3d6e0e8',locator='Butzer1984, Long-Term Nile Flood Variation and Political Discontinuities in Pharaonic Egypt, printedp105/PDFpage4; traditional seasonal cycle')}
SOILS=['Sand','Loamy sand','Sandy loam','Loam','Silt loam','Silt','Silt clay loam','Silty clay','Clay']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


class Rows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,text):
        if self.cell is not None:self.cell.append(text)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None


def numeric_range(raw):
    m=re.fullmatch(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',raw)
    if not m:raise ValueError('Unqualified numeric range required: '+raw)
    return [float(v) for v in m.groups()]


def main(out=OUT):
    CACHE.mkdir(parents=True,exist_ok=True);tables={}
    for name,spec in SOURCES.items():
        p=CACHE/name
        if not p.exists():
            with urllib.request.urlopen(spec['url'],timeout=60) as response:data=response.read()
            assert hashlib.sha256(data).hexdigest()==spec['sha256'],'Source changed; audit required'
            p.write_bytes(data)
        assert sha(p)==spec['sha256'],name
        if name.endswith('.html'):
            text=p.read_text(encoding='latin1');parser=Rows();parser.feed(text)
            # Separate raw-regex parse, with no reuse of the HTMLParser state machine.
            independent=[]
            for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text,re.S|re.I):
                cells=[' '.join(unescape(re.sub(r'<[^>]*>','',cell)).split()) for cell in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S|re.I)]
                independent.append(cells)
            selected=[row for row in parser.rows if row and ((name=='fao56_ch7.html' and row[0] in SOILS and len(row)==6) or (name=='fao56_ch8.html' and row[0] in ('Barley','Winter Wheat') and len(row)==3 and '-' in row[1]))]
            for row in selected:assert independent.count(row)==1,row
            tables[name]=selected
    soils=[]
    for name in SOILS:
        rows=[r for r in tables['fao56_ch7.html'] if r[0]==name];assert len(rows)==1;row=rows[0]
        soils.append(dict(soil=name,available_water_fraction_range=numeric_range(row[3]),surface_REW_mm_range=numeric_range(row[4]),surface_TEW_mm_range_at_0p10m=numeric_range(row[5])))
    roots=[]
    for name in ('Barley','Winter Wheat'):
        rows=[r for r in tables['fao56_ch8.html'] if r[0]==name];assert len(rows)==1;row=rows[0]
        roots.append(dict(crop=name,maximum_root_depth_m_range=numeric_range(row[1]),p_at_ET5mm_day=float(row[2])))
    envelopes=[]
    for crop in roots:
        for soil in soils:
            values=[float(Decimal(str(a))*Decimal(str(b))*1000) for a,b in zip(crop['maximum_root_depth_m_range'],soil['available_water_fraction_range'])]
            # Independent float arithmetic check of the unit conversion and envelope endpoints.
            for j,value in enumerate(values):assert abs(value-1000*crop['maximum_root_depth_m_range'][j]*soil['available_water_fraction_range'][j])<1e-10
            envelopes.append(dict(crop=crop['crop'],soil=soil['soil'],generic_TAW_mm_range=values))
    upper={crop['crop']:max(v['generic_TAW_mm_range'][1] for v in envelopes if v['crop']==crop['crop']) for crop in roots}
    assert upper=={'Barley':300.,'Winter Wheat':360.}
    result=dict(status='generic_source_constraints_only',producer_sha256=sha(Path(__file__)),sources=SOURCES,soil_table19=soils,crop_table22=roots,generic_root_zone_envelopes=envelopes,
        generic_maximum_TAW_mm=upper,not_local_soil_measurements=True,parameters_adopted=False,field_runs_recomputed=False,
        source_interpretation='FAO separates shallow surface evaporation from deeper root-zone availability and applies depletion stress. Butzer describes inundation through mid-November in the north and a high post-flood water table; no local quantitative groundwater flux or universal crop duration inferred.',
        next='Declare a separate evaporation-layer/root-zone model and inundation/drainage clock; qualify local soil and groundwater inputs before capacity or harvest adoption. Do not replace field results or choose600mm to close Egypt.')
    out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Two raw table parses agree;9soil types,2crops,18generic envelopes; maxTAW',upper)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
