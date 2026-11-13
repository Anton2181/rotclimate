"""Qualified gauge timing preflight; no irrigation-area or harvest fit."""
import argparse,csv,datetime,hashlib,io,json,re,subprocess,sys
from collections import Counter,defaultdict
from html.parser import HTMLParser
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.flood_timing import crop_flood_timing
from settlement_locations_earth import sha,write
from fetch_flood_gauges import SOURCES
PLAN=ROOT/'calibration/flood_basin_seasonality_20261113/plan.json'
CACHE=ROOT/'data/cache/flood_basin_seasonality_20261113'
OUT=ROOT/'output/flood_basin_seasonality_20261113'


class GaugeTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip());self.cell=None
        elif tag=='tr' and self.row is not None:
            if self.row and re.fullmatch(r'\d{4}-\d{2}-\d{2}',self.row[0]):self.rows.append(self.row)
            self.row=None;self.cell=None


def complete_years(records,year0,year1):
    grouped=defaultdict(list)
    for day,raw in records:
        date=datetime.date.fromisoformat(day)
        if year0<=date.year<=year1:grouped[date.year].append((date.month,raw))
    years=[];values=[];excluded=[]
    for year in range(year0,year1+1):
        data=grouped[year];months=[m for m,_ in data];reason=[]
        if len(data)!=12:reason.append('not_twelve_records')
        if len(set(months))!=len(months):reason.append('duplicate_month')
        parsed=[]
        for month,raw in data:
            # A qualifier is not permission to silently use a censored value.
            try:value=float(raw)
            except (ValueError,TypeError):value=float('nan')
            if not np.isfinite(value) or value<0:reason.append('invalid_or_qualified_flow')
            parsed.append((month,value))
        if reason:excluded.append(dict(year=year,records=len(data),reasons=sorted(set(reason))))
        else:years.append(year);values.append([q for _,q in sorted(parsed)])
    return years,np.asarray(values,dtype=float).reshape(-1,12),excluded


def main(out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    out.mkdir(parents=True,exist_ok=True);plan=json.loads(PLAN.read_text());rows=[];fields={};sources={}
    controls=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_flood_timing.py','tests/test_flood_gauge_quality.py'],cwd=ROOT,capture_output=True,text=True,check=True)
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/flood_timing.py',PLAN]};write(out/'controls.json',dict(status='passed_before_phase_outputs',output=controls.stdout,producers=producers))
    for name,spec in SOURCES.items():
        assert sha(CACHE/name)==spec['sha256'],f'Source bytes changed: {name}'
    raw=[]
    for spec in plan['sources'][:2]:
        key=spec['id'];path=CACHE/(key+'.html');sources[str(path.relative_to(ROOT))]=sha(path);parser=GaugeTable();parser.feed(path.read_text());assert parser.rows and all(len(v)==2 for v in parser.rows)
        dates=[v[0] for v in parser.rows];assert len(dates)==len(set(dates)),key
        raw.extend([key,*v] for v in parser.rows)
        years,flow,excluded=complete_years(parser.rows,*spec['primary_years']);qualified=len(years)>=5
        item=dict(id=key,doi=spec['doi'],role=spec['role'],source_format='PANGAEA HTML representation of same DOI; text endpoint unavailable',source_rows=len(parser.rows),source_date_min=min(dates),source_date_max=max(dates),primary_years=spec['primary_years'],complete_years=years,excluded_years=excluded,qualified_for_phase=qualified,flow_units='m3/s',not_an_ancient_discharge_reconstruction=True)
        if qualified:
            mean=flow.mean(axis=0);fields[key+'__complete_years']=np.asarray(years);fields[key+'__monthly_flow']=flow;fields[key+'__mean_flow']=mean
            item.update(mean_monthly_flow_m3s=mean.tolist(),peak_month=int(mean.argmax())+1,phase=[])
            for duration in range(3,10):
                r=crop_flood_timing(mean,crop_months=duration)
                for name,value in r.items():fields[key+f'__crop{duration}__'+name]=value
                item['phase'].append(dict(crop_months=duration,**{name:value.tolist() for name,value in r.items()}))
            primary=next(v for v in item['phase'] if v['crop_months']==5);item['november_illustration']={n:primary[n][10] for n in ('pre_sowing_excess_share','standing_crop_excess_share','compatibility')}
        rows.append(item)
    path=CACHE/'dai.nc';assert hashlib.md5(path.read_bytes()).hexdigest()=='9e0d54ba504a95f46b75a6be226f7c5b';sources[str(path.relative_to(ROOT))]=sha(path);sources[str((CACHE/'dai_readme.txt').relative_to(ROOT))]=sha(CACHE/'dai_readme.txt')
    with netcdf_file(path,'r',mmap=False) as nc:
        decode=lambda a:a.tobytes().decode('latin1').split('\x00')[0].strip()
        indices=[i for i,v in enumerate(nc.variables['riv_name'][:]) if decode(v).casefold()=='indus']
        assert len(indices)==1,'Require unambiguous author river identifier'
        i=indices[0];start=int(nc.variables['yrb'][i]);end=int(nc.variables['yre'][i]);assert start>1931,'New earlier coverage needs an explicit source audit before unmasking the heldout phase'
        rows.append(dict(id='indus',role='heldout_phase_check',source='Dai2025 Kotri downstream station',doi='10.5281/zenodo.17379716',station_name=decode(nc.variables['stn_name'][i]),station_id=int(nc.variables['id'][i]),author_record_start=start,author_record_end=end,primary_years=[1900,1931],complete_years=[],qualified_for_phase=False,status='unscored_pre1932_record_unavailable',phase_values_inspected=False,reason='Primary record starts after Sukkur barrage1932. No post-regulation substitution. FLOW_1800 index mapping is not certified for this station and is not guessed.'))
    np.savez_compressed(out/'fields.npz',**fields)
    b=io.StringIO(newline='');writer=csv.writer(b);writer.writerow(['station','crop_months','sowing_month','pre_sowing_excess_share','standing_crop_excess_share','compatibility'])
    for r in rows:
        for phase in r.get('phase',[]):
            for sow in range(12):writer.writerow([r['id'],phase['crop_months'],sow+1,*[phase[n][sow] for n in ('pre_sowing_excess_share','standing_crop_excess_share','compatibility')]])
    (out/'phase.csv').write_text(b.getvalue())
    b=io.StringIO(newline='');writer=csv.writer(b);writer.writerow(['station','date','monthly_mean_m3s']);writer.writerows(raw)
    (out/'gauge_monthly.csv').write_text(b.getvalue())
    write(out/'sources.json',SOURCES)
    protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()}
    producers['scripts/fetch_flood_gauges.py']=sha(ROOT/'scripts/fetch_flood_gauges.py')
    write(out/'results.json',dict(status='gauge_phase_preflight_only',rows=rows,sources=sources,producers=producers,files_sha256={n:sha(out/n) for n in ('fields.npz','phase.csv','gauge_monthly.csv','sources.json')},unchanged_atlas_sha256=protected,irrigation_or_harvest_scores_computed=False,heldout_phase_qualified=False,adopt=False,limits='Phase compatibility is not usable water volume or irrigated fraction;the original HAND/area/capacity and whole-empire calibration have not changed.'))
    print([(r['id'],len(r['complete_years']),r.get('peak_month'),r.get('november_illustration')) for r in rows])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
