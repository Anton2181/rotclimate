"""Publish all reviewed regional forcing substitutions and complete water maps."""
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

OUT=ROOT/'output/regional_reference_forcing_20261114'
PAGE=ROOT/'atlases/earth_evidence/regional_forcing'
REGIONS={'nile':'Nile','mesopotamia_euphrates_only':'Mesopotamia · Euphrates only'}
FORCINGS={'legacy_archive':'Archived forcing','power_hargreaves':'Regional Hargreaves','power_penman_monteith':'Regional Penman–Monteith'}


def case_cells(row):
    return [REGIONS[row['region']],'5-bin' if row['calendar']=='old' else '4-bin fractional','Capture' if row['capture'] else 'Rain only',FORCINGS[row['forcing']],f"{100*row['root_coverage']:.2f}%",f"{row['eligible_area_km2']:,.0f}",f"{row['adequate_root_area_km2']:,.0f}",f"{row['delivered_m3']/1e9:.3f}",f"{row['pond_evap_m3']/1e9:.3f}",str(row['spinup_years'])]


def coverage_cells(region,row):
    return [REGIONS[region],str(row['candidate_fields']),str(row['weather_cells']),f"{row['area_weighted_distance_km']:.2f}",f"{row['maximum_distance_km']:.2f}",*[f'{row[name]:,.1f}' for name in ['legacy_area_weighted_annual_eto_mm','power_hargreaves_area_weighted_annual_eto_mm','power_penman_monteith_area_weighted_annual_eto_mm']]]


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    weather=json.loads((OUT/'weather.json').read_text());wr=json.loads((OUT/'weather_review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_regional_reference_fields.py')
    assert wr['reviewer_sha256']==sha(ROOT/'scripts/review_regional_reference_weather.py')
    for record in [r,weather]:
        for name,digest in {**record['producers'],**record['sources'],**record['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for receipt in [review,wr]:
        for name,digest in receipt['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    colors=['#73868d','#b67836','#2a817b']
    for j,(region,label) in enumerate(REGIONS.items()):
        for k,calendar in enumerate(['old','fractional']):
            ax=axes[j,k]
            for offset,(forcing,caption) in enumerate(FORCINGS.items()):
                values=[100*next(row['root_coverage'] for row in r['rows'] if row['region']==region and row['calendar']==calendar and row['capture']==capture and row['forcing']==forcing) for capture in [False,True]]
                ax.bar(np.arange(2)+(offset-1)*.23,values,width=.23,color=colors[offset],label=caption)
            ax.set_xticks([0,1],['Rain only','River capture']);ax.set_ylim(0,100);ax.set_ylabel('Root demand met (%)');ax.grid(axis='y',alpha=.2)
            ax.set_title(label+' · '+('5-bin' if calendar=='old' else '4-bin fractional'),fontsize=10)
    handles,labels=axes[0,0].get_legend_handles_labels();axes[0,0].legend(handles,labels,loc='upper left',fontsize=8)
    fig.suptitle('All 24 paired water scenarios · only evaporation forcing changes',fontsize=14)
    fig.supxlabel('Fixed barley/profile/calendar policies; modern regional ETo with archived T/P is a declared sensitivity, not a climate reconstruction.',fontsize=8)
    fig.savefig(OUT/'paired_root_coverage.png',dpi=160);plt.close(fig)
    with np.load(OUT/'fields.npz') as z,np.load(OUT/'forcing.npz') as f:
        fig,axes=plt.subplots(4,3,figsize=(12,14),layout='constrained')
        for row_index,(region,calendar) in enumerate([(a,b) for a in REGIONS for b in ['old','fractional']]):
            lat=f[region+'__lat'];lon=f[region+'__lon']
            for col,(forcing,caption) in enumerate(FORCINGS.items()):
                row=next(v for v in r['rows'] if v['region']==region and v['calendar']==calendar and v['capture'] and v['forcing']==forcing)
                case=row['case'];eligible=z[case+'__eligible'];ax=axes[row_index,col]
                ax.scatter(lon,lat,c='#d7d9d8',marker='s',s=8)
                im=ax.scatter(lon[eligible],lat[eligible],c=z[case+'__root_coverage'][eligible],cmap='viridis',vmin=0,vmax=1,marker='s',s=9)
                ax.set_title(REGIONS[region]+'\n'+('5-bin' if calendar=='old' else '4-bin fractional')+'\n'+caption+f" · {100*row['root_coverage']:.1f}%",fontsize=8)
                ax.set_xlabel('Longitude (°E)');ax.set_ylabel('Latitude (°N)');ax.set_aspect(1/np.cos(np.deg2rad(lat.mean())));ax.grid(alpha=.12)
        fig.colorbar(im,ax=axes,label='Root transpiration actual / potential',shrink=.65)
        fig.suptitle('Regional forcing changes field-water diagnostics · river capture cases',fontsize=14)
        fig.supxlabel('One-degree sampled weather drives five-minute candidate fields; grey is crop-ineligible terrain, still in the water ledger.\nBarley, supplied 1.5 m roots/TAW 225 mm, bare coefficient 0.15, pond 200 mm, efficiency 1. No harvest or settlement adoption.',fontsize=9)
        fig.savefig(OUT/'regional_root_water_maps.png',dpi=160);plt.close(fig)
    source=ROOT/'data/source/regional_reference_forcing_20261114'
    with zipfile.ZipFile(OUT/'weather_sources.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(source.glob('*.json')):
            info=zipfile.ZipInfo(path.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            archive.writestr(info,path.read_bytes())
    PAGE.mkdir(parents=True,exist_ok=True)
    files=['results.json','review.json','weather.json','weather_review.json','forcing.npz','assignments.csv','weather_daily.csv.gz','fields.npz','fields.csv.gz','weather_sources.zip','paired_root_coverage.png','regional_root_water_maps.png']
    for name in files:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/regional_reference_forcing_20261114/plan.json',PAGE/'plan.json')
    shutil.copyfile(OUT/'core/review.json',PAGE/'core_review.json')
    cases=''.join(f'<tr data-region="{v["region"]}" data-calendar="{v["calendar"]}" data-access="{int(v["capture"])}">'+''.join('<td>'+escape(cell)+'</td>' for cell in case_cells(v))+'</tr>' for v in r['rows'])
    coverage=''.join('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in coverage_cells(region,v))+'</tr>' for region,v in weather['regions'].items())
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Declared protocol'),('core_review.json','Shared-adapter checks'),('weather.json','Regional weather/coverage facts'),('weather_review.json','Independent weather review'),('results.json','All 24 field results'),('review.json','Independent field review/replay'),('forcing.npz','Regional forcing arrays'),('assignments.csv','All 1,507 field assignments (CSV)'),('weather_daily.csv.gz','All 54,810 computed weather days (gzip CSV)'),('fields.npz','Field states/fluxes and basin ledgers'),('fields.csv.gz','All 18,084 field rows (gzip CSV)'),('weather_sources.zip','All frozen raw weather and source receipt (ZIP)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Regional evaporation forcing · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1250px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column;max-width:100%}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../reference_eto/">Three-location weather audit</a> · <a href="../daily_fields/">Earlier daily water maps</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Regional evaporation forcing changes the field-water result</h1><p class="status">All 1,507 candidate fields now have an explicit regional weather assignment and paired forcing controls. The 24 retained water scenarios show material sensitivity to the reference method. These are conditional water maps, with no new harvest or settlement adoption.</p></header>
<section><h2>The paired result</h2><p>For the five-bin Nile crop with capture, root-demand coverage is 65.3% under archived forcing, 68.3% under regional Hargreaves and 52.4% under regional Penman–Monteith. The shorter supplied crop gives 79.0%, 80.8% and 66.1%. All cases retain the same soil, crop coefficient, river supply and pond/drainage rules. No calendar or parameter is selected from these scores.</p><figure><a href="paired_root_coverage.png" download><img src="paired_root_coverage.png" width="1760" height="1120" alt="All 24 paired root-water results across Nile and Euphrates-only candidates, both supplied crop calendars and rain-only/capture access, under three fixed evaporation forcing choices."></a><figcaption>Root-demand coverage is actual/potential root transpiration. It is not grain yield, total crop ET coverage, cultivated area or population. Mesopotamia remains Euphrates only; the Tigris is absent.</figcaption></figure><figure><a href="regional_root_water_maps.png" download><img src="regional_root_water_maps.png" width="1920" height="2240" alt="Twelve river-capture maps retain both regions and both supplied calendars under archived, regional Hargreaves and regional Penman-Monteith forcing, with one common root-water scale."></a><figcaption>All candidates remain water consumers, including thermally ineligible grey fields. Five-minute field display does not imply five-minute weather resolution.</figcaption></figure></section>
<section><h2>Full coverage with a declared sampling policy</h2><p>Each field is assigned to the centre of its containing one-degree tile. The 30 fixed samples supply 54,810 complete 2020–2024 NASA POWER daily records. This is a sampling lattice, not NASA's native resolution or a downscaling model. Distances and provider grid elevations are exported for every field; no candidates are removed for being inconvenient.</p><div class="table" tabindex="0" aria-label="Regional weather assignment and evaporation coverage"><table id="coverage"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Region','Fields','Weather samples','Mean distance km','Max distance km','Archived ETo mm/year','Regional Hargreaves mm/year','Regional PM mm/year'])}</tr></thead><tbody>{coverage}</tbody></table></div><p>Annual reference-demand means above use candidate-area weights. Five-year Gregorian monthly totals map conservatively into the twelve existing equal model bins, including leap-day amounts. Hargreaves and PM share weather, solar geometry, grid assignment and temporal mapping; their difference isolates the method. Archived versus regional Hargreaves also changes weather source, period, geometry and aggregation.</p></section>
<section><h2>Every paired field case</h2><p>All cases fix barley, supplied 1.5 m roots (TAW 225 mm), bare coefficient 0.15, pond 200 mm and efficiency 1. Rain-only controls retain the same pond/drainage policy. “≥95% root” is an unvalidated water diagnostic, not productive hectares. Eight archived controls reproduce every original field/state/flux/basin array exactly.</p><div class="filters"><label>Region<select id="region"><option value="">Both regions</option>{''.join(f'<option value="{key}">{value}</option>' for key,value in REGIONS.items())}</select></label><label>Calendar<select id="calendar"><option value="">Both supplied calendars</option><option value="old">5-bin</option><option value="fractional">4-bin fractional</option></select></label><label>Access<select id="access"><option value="">Rain only and capture</option><option value="0">Rain only</option><option value="1">Capture</option></select></label></div><p id="count" role="status">24 scenarios</p><div class="table" tabindex="0" aria-label="Paired regional field-water cases"><table id="cases"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Region','Calendar','Access','Evaporation forcing','Root demand met','Eligible km²','≥95% root km²','Delivered km³','Pond ET km³','Cycles'])}</tr></thead><tbody>{cases}</tbody></table></div></section>
<section><h2>What remains unqualified</h2><p>The substituted evaporation uses modern 2020–2024 model/satellite weather, while the frozen field temperature/rain inputs come from WorldClim 1970–2000. This is an evaporation-only sensitivity with an explicit period/input mismatch, not a consistent reconstruction of ancient climate. Coarse weather cells can mix valley, desert, coast and elevated terrain. Grid completeness is not local validation.</p><p>Constant legacy crop demand, Kcmax, exposed soil fraction, root depth, soil profile and inundation/drainage remain supplied approximations, without local or wind/humidity adjustment. No point ratios, fitted correction or crop-stage curve is applied. Neither method is measured crop ET, and all cases are exposed development.</p><p>The shared adapter now accepts explicit world extraterrestrial radiation and weather, so its algebra can serve Earth or another world. It does not invent missing vapour, 2 m wind or solar data from the old fantasy harvest cache. That connection remains a separate input-qualification task.</p></section>
<section><h2>Independent checks and complete downloads</h2><p>182 controls pass. The shared adapter has 17,000 independent scalar/Decimal checks and 3,600 bin-amount checks. Regional review reconstructs all 931,770 computed weather cells and 1,507 assignments. Field review replays all {review['final_cycle_field_steps']:,} final-cycle field-steps, checks annual field states/fluxes, monthly basin ledgers, daily basin stocks and all 18,084 CSV rows. Every case reaches periodic stocks in two cycles. Seven fresh numeric exports reproduce byte for byte; 923 protected files remain unchanged.</p><p>{links}</p></section>
<section><h2>Next dependency</h2><p>Resolve climate period/grid consistency and qualify regional weather before adopting a reference-forcing rule. Keep local crop phenology, basal diffusion versus root uptake, canopy/root development, soil and pond/drainage evidence open. Tigris, shared Earth/fantasy river flow and independent regions remain required before freezing harvest translation and testing Nile gain and Mesopotamian non-inflation.</p><p>Release-3 settlements and marketed share 0.3923 remain current; whole-empire Egypt calibration still fails. These maps do not change food supply, residents, institutions or authority.</p></section></main>
<script>function filter(){{let n=0;for(const row of document.querySelectorAll('#cases tbody tr')){{row.hidden=['region','calendar','access'].some(key=>{{const value=document.getElementById(key).value;return value&&row.dataset[key]!==value;}});if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' scenarios';}}for(const key of ['region','calendar','access'])document.getElementById(key).addEventListener('change',filter);</script></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';old=index.read_text();old=re.sub(r'<section id="regional-reference-forcing">.*?</section>','',old,flags=re.S)
    panel='<section id="regional-reference-forcing"><h2>Regional forcing now has paired field-water maps</h2><p>All 1,507 fields and 24 fixed cases retain complete weather assignment and exact legacy controls. <a href="regional_forcing/">Open the new comparison maps, full grid and independent ledgers →</a></p></section>'
    index.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),weather_review_sha256=sha(OUT/'weather_review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
