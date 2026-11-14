"""Publish every reviewed daily river/pond/soil development case."""
import json,re,shutil,sys
from html import escape
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/daily_river_fields_20261114';PAGE=ROOT/'atlases/earth_evidence/daily_fields'
LABELS={'nile':'Nile','mesopotamia_euphrates_only':'Mesopotamia · Euphrates only'}


def cells(v):
    return [LABELS[v['region']],v['crop'],f'{v["root_depth_m"]:g}','5-bin' if v['calendar']=='old' else '4-bin fractional',f'{v["bare_background"]:g}',f'{v["pond_capacity_mm"]:g}',f'{v["efficiency"]:g}','Capture' if v['capture'] else 'Rain only',f'{100*v["root_coverage"]:.1f}%' if v['root_coverage'] is not None else 'Unscored',f'{v["eligible_area_km2"]:,.0f}',f'{v["adequate_root_area_km2"]:,.0f}' if v['adequate_root_area_km2'] is not None else 'Unscored',f'{v["delivered_m3"]/1e9:.3f}',f'{v["pond_evap_m3"]/1e9:.3f}']


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_daily_river_fields.py')
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for j,region in enumerate(LABELS):
        for k,crop in enumerate(('barley','wheat')):
            ax=axes[j,k];groups=[];names=[]
            for calendar in ['old','fractional']:
                for capture in [False,True]:
                    group=[100*v['root_coverage'] for v in r['rows'] if v['region']==region and v['crop']==crop and v['calendar']==calendar and v['capture']==capture and v['root_coverage'] is not None]
                    groups.append(group);names.append(('5-bin' if calendar=='old' else '4-bin fractional')+'\n'+('capture' if capture else 'rain only'))
            ax.boxplot(groups,positions=range(1,5),whis=(0,100),widths=.5,showfliers=False)
            for x,group in enumerate(groups,1):ax.scatter(x+np.linspace(-.17,.17,len(group)),group,s=13,color='#27778b' if x%2==0 else '#a46929',alpha=.65)
            ax.set_xticks(range(1,5),names,fontsize=8);ax.set_ylim(-2,102);ax.set_ylabel('Root transpiration demand met (%)');ax.grid(axis='y',alpha=.2);ax.set_title(LABELS[region]+' · '+crop,fontsize=11)
    fig.suptitle('All 256 daily development cases · matched rain-only and capture controls',fontsize=14)
    fig.supxlabel('Dots are declared parameter combinations; whiskers show their full spread, not confidence intervals.\nRoot coverage is not the earlier total-crop ET metric, grain yield or historical population.',fontsize=9)
    fig.savefig(OUT/'scenario_spread.png',dpi=160);plt.close(fig)
    with np.load(OUT/'fields.npz') as z:
        fig,axes=plt.subplots(2,4,figsize=(15,9),layout='constrained')
        for j,region in enumerate(LABELS):
            lat=z[region+'__lat'];lon=z[region+'__lon']
            for k,(calendar,capture) in enumerate([(a,b) for a in ['old','fractional'] for b in [False,True]]):
                row=next(v for v in r['rows'] if v['region']==region and v['crop']=='barley' and v['root_depth_m']==1.5 and v['calendar']==calendar and v['bare_background']==.15 and v['pond_capacity_mm']==200 and v['efficiency']==1 and v['capture']==capture)
                case=row['case'];ok=z[case+'__eligible'];ax=axes[j,k];ax.scatter(lon,lat,c='#d7d9d8',marker='s',s=7)
                im=ax.scatter(lon[ok],lat[ok],c=z[case+'__root_coverage'][ok],marker='s',s=8,vmin=0,vmax=1,cmap='viridis')
                ax.set_title(LABELS[region]+'\n'+('5-bin' if calendar=='old' else '4-bin fractional')+' · '+('capture' if capture else 'rain only'),fontsize=9)
                ax.set_xlabel('Longitude (°E)');ax.set_ylabel('Latitude (°N)');ax.set_aspect(1/np.cos(np.deg2rad(lat.mean())));ax.grid(alpha=.12)
        fig.colorbar(im,ax=axes,label='Root transpiration actual / potential',shrink=.7)
        fig.suptitle('Daily water routing on candidate fields · no settlement or harvest adoption',fontsize=14)
        fig.supxlabel('Fixed illustration: barley, supplied loam profile, 1.5 m roots (TAW 225 mm), bare coefficient 0.15, pond 200 mm, efficiency 1.\nGrey is crop-ineligible terrain; all candidates still consume water. Uniform within-bin rain/flow; no preferred case selected.',fontsize=9)
        fig.savefig(OUT/'daily_field_maps.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['results.json','review.json','fields.npz','fields.csv.gz','scenario_spread.png','daily_field_maps.png']:shutil.copyfile(OUT/name,PAGE/name)
    for name in ['plan.json','geometry_policy.json']:shutil.copyfile(ROOT/'calibration/daily_river_fields_20261114'/name,PAGE/name)
    shutil.copyfile(OUT/'core/review.json',PAGE/'core_review.json')
    table=''.join(f'<tr data-region="{v["region"]}" data-crop="{v["crop"]}" data-calendar="{v["calendar"]}">'+''.join('<td>'+escape(x)+'</td>' for x in cells(v))+'</tr>' for v in r['rows'])
    headers=['Region','Crop','Root m','Calendar','Bare coefficient','Pond mm','Efficiency','Access','Root demand met','Eligible km²','≥95% root km²','Delivered km³','Pond ET km³']
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Protocol'),('geometry_policy.json','Candidate-area policy'),('core_review.json','Core checks'),('results.json','All results/provenance'),('review.json','Independent review/replay'),('fields.csv.gz','All field rows (gzip CSV)'),('fields.npz','Field states/monthly ledgers (NPZ)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Daily river, pond and crop-water development · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1250px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column;min-width:0;max-width:100%}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../soil_drying/">Soil component checks</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>River water now reaches finite ponds and daily soil stores</h1><p class="status">The daily coupling is implemented and all 256 declared development cases are retained. These are water-budget scenarios with unqualified field parameters and forcing, not a calibrated harvest or settlement update.</p></header>
<section><h2>One paid chain from river to field</h2><p>River withdrawals are limited once at each node and rationed among fields by useful request. Delivery losses, finite infiltration, pond storage, pond evaporation, drainage, surface drying, deeper bare-soil diffusion and crop root uptake share the same water ledger. Drained water leaves this model; it is not credited again downstream.</p><p>The complete bare-soil FAO example now pays its deeper background evaporation separately, with zero crop uptake. All terrain candidates retain their water demand even when the prescribed crop is thermally ineligible.</p></section>
<section><h2>All declared cases and matched controls</h2><p>Two supplied calendars, two root depths, two bare coefficients, two pond capacities and two efficiencies are retained for both crops and regions, each with a rain-only control. The spread below describes the scenario grid, not statistical uncertainty.</p><figure><a href="scenario_spread.png" download><img src="scenario_spread.png" width="1920" height="1280" alt="Four panels retain all 256 conditional root-water cases for barley and wheat on Nile and Euphrates candidate fields, comparing rain-only and river-capture cases under both supplied calendars."></a><figcaption>The metric is root transpiration actual/potential. It is not the previous monthly total-crop ET coverage, crop yield, irrigated hectares or residents.</figcaption></figure>
<figure><a href="daily_field_maps.png" download><img src="daily_field_maps.png" width="2400" height="1440" alt="Eight daily root-water maps compare matched rain-only and capture cases for both candidate regions and both supplied calendars. All use one stated illustrative profile, not a fitted or adopted case."></a><figcaption>The maps illustrate a fixed member of the grid without selecting it for adoption. Crop-ineligible candidates remain in the flood-water ledger; their crop scores are unreported.</figcaption></figure></section>
<section><h2>Every development row</h2><p>The supplied loam profiles have TAW 150/225 mm, not 600 mm. Neither profile is a local measurement. “≥95% root” is a water-demand diagnostic, not validated productive or cultivated area. Scroll the table horizontally to see all metrics.</p><div class="filters"><label>Region<select id="region"><option value="">Both regions</option><option value="nile">Nile</option><option value="mesopotamia_euphrates_only">Mesopotamia · Euphrates only</option></select></label><label>Crop<select id="crop"><option value="">Both crops</option><option value="barley">Barley</option><option value="wheat">Wheat</option></select></label><label>Calendar<select id="calendar"><option value="">Both supplied calendars</option><option value="old">5-bin</option><option value="fractional">4-bin fractional</option></select></label></div><p id="count" role="status">256 scenarios</p><div class="table" tabindex="0" aria-label="Daily water scenario table, horizontally scrollable"><table><thead><tr>{''.join('<th scope="col">'+h+'</th>' for h in headers)}</tr></thead><tbody>{table}</tbody></table></div></section>
<section><h2>Independent checks</h2><p>105 controls pass. The core audit checks the full bare FAO example and 100 synthetic drainage forests. A separate compiled scalar implementation balances {review['field_days']:,} final-cycle field-steps, reproduces spin-up convergence, and compares annual field states/fluxes, monthly basin ledgers, daily basin stocks and all {review['csv_rows']:,} CSV rows. All 256 cases reach repeating annual stocks. Three fresh numeric files reproduce byte for byte; 904 Earth-fit files and both earlier field/component data sets remain unchanged.</p><p>{links}</p></section>
<section><h2>What still needs evidence</h2><p>Monthly climate and gauge volumes are spread uniformly inside their bins. That is not daily weather: frequent small amounts can evaporate near the surface while storms would infiltrate differently. Local rain timing, soil profiles, root development, crop coefficients, infiltration, pond access and drainage dates remain unqualified.</p><p>The constant legacy crop coefficient is used here only as a supplied root-demand coefficient; it is not a calibrated basal crop curve or the old total-ET/yield model. Pond coverage suppresses soil ET for the whole step by a declared approximation. Both calendars and the ideal shared river pool are scenarios, with no chosen winner.</p><p>Mesopotamia still receives only Euphrates water; the Tigris is absent. These development diagnostics cannot establish regional non-inflation, independent transfer or a whole-empire harvest calibration. The current release-3 settlements, marketed share 0.3923 and Egypt calibration failure remain unchanged.</p></section></main>
<script>function filter(){{let n=0;const ids=['region','crop','calendar'];for(const row of document.querySelectorAll('tbody tr')){{row.hidden=ids.some(id=>{{const v=document.getElementById(id).value;return v&&row.dataset[id]!==v;}});if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' scenarios';}}for(const id of ['region','crop','calendar'])document.getElementById(id).addEventListener('change',filter);</script></html>'''
    (PAGE/'index.html').write_text(html)
    evidence=ROOT/'atlases/earth_evidence/index.html';old=evidence.read_text();old=re.sub(r'<section id="daily-river-fields">.*?</section>','',old,flags=re.S)
    panel='<section id="daily-river-fields"><h2>Daily river-to-field water is connected</h2><p>256 matched development cases now include finite ponds, paid delivery, bare diffusion and daily soil/root water. <a href="daily_fields/">Open all scenarios, new field maps and independent water ledgers →</a></p></section>'
    evidence.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(evidence)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
