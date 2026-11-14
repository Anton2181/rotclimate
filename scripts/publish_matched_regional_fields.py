"""Publish all paired matched-meteorology water cases and reviewed inputs."""
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write

OUT=ROOT/'output/matched_regional_fields_20261114'
INPUT=ROOT/'output/matched_regional_weather_20261114'
PAGE=ROOT/'atlases/earth_evidence/matched_weather'
REGIONS={'nile':'Nile','mesopotamia_euphrates_only':'Euphrates only'}
METHODS={'hargreaves':'Hargreaves','penman_monteith':'Penman–Monteith'}
MET={'eto_only':'Archived T/P + modern ETo','matched':'Matched modern T/P/ETo'}


def case_cells(row):
    return [REGIONS[row['region']],'5-bin' if row['calendar']=='old' else '4-bin fractional','Capture' if row['capture'] else 'Rain only',METHODS[row['method']],MET[row['meteorology']],f"{100*row['root_coverage']:.2f}%",f"{row['eligible_area_km2']:,.0f}",f"{row['adequate_root_area_km2']:,.0f}",f"{row['delivered_m3']/1e9:.3f}",str(row['spinup_years'])]


def main():
    r=json.loads((OUT/'results.json').read_text());v=json.loads((OUT/'review.json').read_text())
    weather=json.loads((INPUT/'weather.json').read_text());wr=json.loads((INPUT/'review.json').read_text())
    assert v['status']=='passed' and v['results_sha256']==sha(OUT/'results.json')
    assert v['reviewer_sha256']==sha(ROOT/'scripts/review_matched_regional_fields.py')
    assert wr['reviewer_sha256']==sha(ROOT/'scripts/review_matched_regional_weather.py')
    for record in [r,weather]:
        for name,digest in {**record['producers'],**record['sources'],**record['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for receipt,base in [(v,OUT),(wr,INPUT)]:
        for name,digest in receipt['fresh_byte_exact'].items():assert sha(base/name)==digest,name
    combinations=[(method,met) for method in METHODS for met in MET];colors=['#b39261','#387b60','#9dabc0','#375985']
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for j,(region,label) in enumerate(REGIONS.items()):
        for k,calendar in enumerate(['old','fractional']):
            ax=axes[j,k]
            for offset,(method,met) in enumerate(combinations):
                values=[100*next(row['root_coverage'] for row in r['rows'] if row['region']==region and row['calendar']==calendar and row['capture']==capture and row['method']==method and row['meteorology']==met) for capture in [False,True]]
                ax.bar(np.arange(2)+(offset-1.5)*.19,values,width=.19,color=colors[offset],label=METHODS[method]+' · '+('ETo only' if met=='eto_only' else 'Matched T/P/ETo'))
            ax.set_xticks([0,1],['Rain only','River capture']);ax.set_ylim(0,100);ax.set_ylabel('Root demand met (%)');ax.grid(axis='y',alpha=.2)
            ax.set_title(label+' · '+('5-bin' if calendar=='old' else '4-bin fractional'),fontsize=11)
    axes[0,0].legend(loc='upper left',fontsize=8)
    fig.suptitle('All 32 paired water scenarios · matched meteorology versus ETo-only controls',fontsize=14)
    fig.supxlabel('Modern T/P/ETo share period and samples. Historical river means, fixed crop/soil/pond assumptions remain. No harvest or settlement adoption.',fontsize=8)
    fig.savefig(OUT/'paired_root_coverage.png',dpi=160);plt.close(fig)
    with np.load(OUT/'fields.npz') as z,np.load(INPUT/'forcing.npz') as f:
        fig,axes=plt.subplots(4,2,figsize=(11,15),layout='constrained')
        for i,(region,calendar) in enumerate((a,b) for a in REGIONS for b in ['old','fractional']):
            lat=f[region+'__lat'];lon=f[region+'__lon']
            for j,met in enumerate(MET):
                row=next(v for v in r['rows'] if v['region']==region and v['calendar']==calendar and v['capture'] and v['method']=='penman_monteith' and v['meteorology']==met)
                case=row['case'];eligible=z[case+'__eligible'];ax=axes[i,j]
                ax.scatter(lon,lat,c='#d7d9d8',marker='s',s=9)
                im=ax.scatter(lon[eligible],lat[eligible],c=z[case+'__root_coverage'][eligible],cmap='viridis',vmin=0,vmax=1,marker='s',s=10)
                caption='ETo-only PM' if met=='eto_only' else 'Matched T/P/ETo PM'
                ax.set_title(REGIONS[region]+' · '+('5-bin' if calendar=='old' else '4-bin fractional')+'\n'+caption+f" · {100*row['root_coverage']:.2f}%",fontsize=10)
                ax.set_xlabel('Longitude (°E)');ax.set_ylabel('Latitude (°N)');ax.set_aspect(1/np.cos(np.deg2rad(lat.mean())));ax.grid(alpha=.12)
        fig.colorbar(im,ax=axes,label='Root transpiration actual / potential',shrink=.65,fraction=.025,pad=.04)
        fig.suptitle('Penman–Monteith river-capture cases · every candidate retained',fontsize=14)
        fig.supxlabel('Same 0–1 scale in every panel; grey would indicate thermally ineligible candidates, still in the water ledger.\nBarley, supplied roots 1.5 m/TAW 225 mm, pond 200 mm, efficiency 1. Groundwater disabled. Historical river epochs remain unmatched.',fontsize=9)
        fig.savefig(OUT/'regional_root_water_maps.png',dpi=160);plt.close(fig)
    with zipfile.ZipFile(OUT/'weather_sources.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted((ROOT/'data/source/matched_regional_weather_20261114').glob('*.json')):
            info=zipfile.ZipInfo(path.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;archive.writestr(info,path.read_bytes())
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['results.json','review.json','fields.npz','fields.csv.gz','weather_sources.zip','paired_root_coverage.png','regional_root_water_maps.png']:shutil.copyfile(OUT/name,PAGE/name)
    for name in ['weather.json','forcing.npz','bins.csv','daily.csv.gz']:shutil.copyfile(INPUT/name,PAGE/name)
    shutil.copyfile(INPUT/'review.json',PAGE/'weather_review.json')
    for source,name in [('field_plan.json','field_plan.json'),('plan.json','weather_plan.json')]:shutil.copyfile(ROOT/'calibration/matched_regional_weather_20261114'/source,PAGE/name)
    cases=''.join(f'<tr data-region="{row["region"]}" data-method="{row["method"]}">'+''.join('<td>'+escape(cell)+'</td>' for cell in case_cells(row))+'</tr>' for row in r['rows'])
    downloads=[('field_plan.json','Declared field comparison'),('weather_plan.json','Declared input preflight'),('weather.json','Weather/coverage facts'),('weather_review.json','Independent input review'),('results.json','All 32 results'),('review.json','Independent field replay'),('forcing.npz','All meteorological arrays'),('bins.csv','All 360 sample bins (CSV)'),('daily.csv.gz','All 54,810 daily rows (gzip CSV)'),('fields.npz','All field states/fluxes and ledgers'),('fields.csv.gz','All 24,112 field rows (gzip CSV)'),('weather_sources.zip','All frozen raw weather and receipt (ZIP)')]
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in downloads)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Matched meteorology water maps · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column;max-width:100%}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../regional_forcing/">Earlier evaporation-only maps</a> · <a href="../groundwater_budget/">Finite groundwater budget</a></nav><header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Temperature, rain and evaporation now share a weather period</h1><p class="status">All 32 paired scenarios and 1,507 candidate fields are retained. The matched inputs modestly raise Nile root-water coverage in the fixed members. These are conditional water maps; historical river epochs, local crop/soil assumptions and Earth harvest calibration remain unresolved. No settlement update is adopted.</p></header>
<section><h2>The paired water result</h2><p>With Penman–Monteith demand and river capture, Nile root-demand coverage changes from 52.44% to 53.93% in the five-bin crop and from 66.15% to 67.85% in the shorter supplied crop. Hargreaves changes from 68.27% to 70.83% and from 80.82% to 81.52%. No member or crop season is selected as a calibrated answer.</p><figure><a href="paired_root_coverage.png" download><img src="paired_root_coverage.png" width="1920" height="1280" alt="All 32 paired root-water results for Nile and Euphrates-only candidates, both crop calendars and access policies, under Hargreaves and Penman-Monteith with archived or matched meteorology."></a><figcaption>Root demand met means actual/potential root transpiration. It is not total-crop ET, grain yield, cultivated area or population. All cases use the same 0–100% scale.</figcaption></figure><figure><a href="regional_root_water_maps.png" download><img src="regional_root_water_maps.png" width="1760" height="2400" alt="Eight paired Penman-Monteith capture maps show all Nile and Euphrates-only candidate fields under both fixed calendars, comparing evaporation-only controls with matched temperature and rain."></a><figcaption>These maps show the eight PM capture cases with one shared 0–1 legend. All Hargreaves and rain-only cases remain in the figure, table and downloads. Every candidate is a water consumer. Thermal eligibility is recomputed from the declared temperature choice; all candidates happen to remain eligible here.</figcaption></figure><p>Euphrates-only PM coverage changes from 0.89% to 0.67% and from 1.18% to 0.73%, despite higher annual rain. Annual rain alone does not determine seasonal root supply. The Tigris is absent, so this is not total Mesopotamian water adequacy or a regional non-inflation validation.</p></section>
<section><h2>All cases, including exact controls</h2><p>Barley, supplied 1.5 m roots/TAW 225 mm, bare coefficient 0.15, pond 200 mm, infiltration 20 mm/day, efficiency 1 and the earlier crop/flood clocks remain fixed. Sixteen ETo-only controls reproduce every archived field/state/flux/basin array exactly. Groundwater is disabled. “≥95% root” is an unvalidated water diagnostic.</p><div class="filters"><label>Region<select id="region"><option value="">Both regions</option>{''.join(f'<option value="{key}">{value}</option>' for key,value in REGIONS.items())}</select></label><label>Reference method<select id="method"><option value="">Both methods</option>{''.join(f'<option value="{key}">{value}</option>' for key,value in METHODS.items())}</select></label></div><p id="count" role="status">32 scenarios</p><div class="table" tabindex="0" aria-label="All paired matched-meteorology cases"><table id="cases"><thead><tr>{''.join('<th scope="col">'+v+'</th>' for v in ['Region','Calendar','Access','Reference method','Meteorology','Root demand met','Eligible km²','≥95% root km²','Delivered km³','Cycles'])}</tr></thead><tbody>{cases}</tbody></table></div></section>
<section><h2>What matching resolves, and what it leaves open</h2><p>All 30 fixed samples have complete 2020–2024LST temperature, rainfall and evaporation inputs. All 438,480 overlapping weather values agree exactly with the earlier ETo packets. Rain amounts retain leap days and mean annual totals; monthly temperature means remain physical Celsius values. Modern five-year gridded inputs are not a long climatic normal, station validation or an ancient reconstruction. Monthly means omit daily extremes and interannual variation.</p><p>Area-weighted annual rain changes from 38.45 to 110.05 mm across Nile candidates and from 139.96 to 157.69 mm across Euphrates-only candidates. Period, source and sampling all change. Historical river supply still uses Aswan1871–1901 and selected Hit1965–1971 means, so climate/river epochs remain unmatched. Crop stages, basal versus soil demand, local roots/soils/canopy, drainage and water-table constraints remain unqualified.</p></section>
<section><h2>Independent checks and complete downloads</h2><p>Input review checks all raw weather overlap, date/unit/domain and 50-digit Decimal aggregation, 360 sample bins, all assignments and CSV cells. Field review independently replays {v['final_cycle_field_steps']:,} final-cycle field-steps, every annual field state/flux, monthly basin flow, daily basin stock and all 24,112 CSV rows. All 32 cases converge within 2–16 repeated cycles. Seven fresh input/field files reproduce byte for byte; all 952 protected files remain unchanged.</p><p>{links}</p></section>
<section><h2>Next dependency</h2><p>Qualify local phenology, basal demand and canopy/root development with consistent soil and drainage inputs before translating root-water coverage into harvest. Keep historical forcing/river compatibility, shared Earth/fantasy weather/flow, Tigris, independent regions and frozen harvest gates. The local groundwater source audit did not qualify regional capacities or fluxes.</p><p>Release-3 settlements and marketed share 0.3923 remain adopted; whole-empire Egypt calibration still fails. Food supply, residents and political authority do not follow from these water maps.</p></section></main><script>function filter(){{let n=0;for(const row of document.querySelectorAll('#cases tbody tr')){{row.hidden=['region','method'].some(key=>{{const value=document.getElementById(key).value;return value&&row.dataset[key]!==value;}});if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' scenarios';}}for(const key of ['region','method'])document.getElementById(key).addEventListener('change',filter);</script></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';old=index.read_text();old=re.sub(r'<section id="matched-weather-fields">.*?</section>','',old,flags=re.S)
    panel='<section id="matched-weather-fields"><h2>Matched meteorology now has paired water maps</h2><p>All 32 cases retain 1,507 candidates and sixteen exact archived controls. <a href="matched_weather/">Open the latest field-water maps, inputs and independent ledgers →</a></p></section>'
    index.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),weather_review_sha256=sha(INPUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
