"""Publish all reviewed flood-storage scenarios; preserve current map defaults."""
import hashlib,json,re,shutil,sys
from html import escape
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/flood_basin_storage_20261114';PAGE=ROOT/'atlases/earth_evidence/flood_storage'
REGIONS={'nile':'Nile','mesopotamia_euphrates_only':'Mesopotamia · Euphrates only'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_flood_basin_storage.py')
    for name,digest in {**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    PAGE.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for j,region in enumerate(REGIONS):
        for k,crop in enumerate(('barley','wheat')):
            ax=axes[j,k]
            for bare,color in [(0,'#236d8c'),(1,'#ae6227')]:
                for capture,style in [('none','--'),('pre_sowing_three_months','-')]:
                    data=sorted([v for v in r['rows'] if v['region']==region and v['crop']==crop and v['bare_ET_fraction']==bare and v['capture']==capture and v['efficiency']==1],key=lambda v:v['capacity_mm'])
                    ax.plot([v['capacity_mm'] for v in data],[v['mean_crop_ET_coverage'] for v in data],style,color=color,marker='o',label=f"Bare ET {bare}×PET · {'rain only' if capture=='none' else 'flood capture'}")
                    if capture!='none':
                        lower=sorted([v for v in r['rows'] if v['region']==region and v['crop']==crop and v['bare_ET_fraction']==bare and v['capture']==capture and v['efficiency']==.5],key=lambda v:v['capacity_mm'])
                        ax.fill_between([100,300,600],[v['mean_crop_ET_coverage'] for v in lower],[v['mean_crop_ET_coverage'] for v in data],color=color,alpha=.15)
            ax.set_title(REGIONS[region]+' · '+crop);ax.set_xticks([100,300,600]);ax.set_xlabel('Uncalibrated field water capacity (mm)');ax.set_ylabel('Area-weighted crop ET coverage');ax.set_ylim(-.02,1.04);ax.grid(alpha=.2)
            if j==0 and k==0:ax.legend(fontsize=8,loc='lower right')
    fig.suptitle('Fixed November crop: floodwater benefit depends on retained storage',fontsize=14)
    fig.supxlabel('Five-month crop; above-mean gauge flow; ideal shared river access. Bands: supplied delivery efficiency 0.5–1.\nBoth bare-evaporation limits and every scenario retained. No soil capacity, irrigated area or yield fitted.',fontsize=9)
    fig.savefig(OUT/'storage_sweep.png',dpi=160);plt.close(fig)
    with np.load(OUT/'fields.npz') as archive:
        fig,axes=plt.subplots(2,3,figsize=(12,9),layout='constrained')
        for j,region in enumerate(REGIONS):
            lat=archive[region+'__lat'];lon=archive[region+'__lon']
            for k,capacity in enumerate((100,300,600)):
                row=next(v for v in r['rows'] if v['region']==region and v['crop']=='barley' and v['capacity_mm']==capacity and v['bare_ET_fraction']==1 and v['efficiency']==1 and v['capture']!='none');case=row['case'];idx=archive[case+'__field_index']
                ax=axes[j,k];ax.scatter(lon,lat,c='#d7d9d8',s=8,marker='s')
                im=ax.scatter(lon[idx],lat[idx],c=archive[case+'__coverage'],s=9,marker='s',cmap='viridis',vmin=0,vmax=1)
                ax.set_title(f'{REGIONS[region]}\nStore {capacity} mm',fontsize=10);ax.set_xlabel('Longitude (°E)');ax.set_ylabel('Latitude (°N)');ax.set_aspect(1/np.cos(np.deg2rad(lat.mean())));ax.grid(alpha=.15)
        fig.colorbar(im,ax=axes,label='Actual / potential crop ET',shrink=.7)
        fig.suptitle('Candidate terrain cells: barley water coverage, not settlement capacity',fontsize=14)
        fig.supxlabel('Illustration: bare ET = PET, delivery efficiency = 1, August–October capture; fixed November–March crop.\nGrey: climate missing or thermally ineligible. Candidate-area aggregation at 5 arc-min; no access/drainage validation.',fontsize=9)
        fig.savefig(OUT/'field_water_maps.png',dpi=160);plt.close(fig)
    names=['results.json','review.json','controls.json','fields.npz','fields.csv.gz','storage_sweep.png','field_water_maps.png']
    for name in names:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/flood_basin_storage_20261114/plan.json',PAGE/'plan.json')
    table=[]
    for v in r['rows']:
        cells=[REGIONS[v['region']],v['crop'],str(v['capacity_mm']),str(v['bare_ET_fraction']),f'{v["efficiency"]:g}','Rain only' if v['capture']=='none' else 'Aug–Oct capture',f'{100*v["mean_crop_ET_coverage"]:.1f}%',f'{v["adequate_area_km2"]:,.0f}',f'{v["delivered_m3"]/1e9:.3f}',f'{v["loss_m3"]/1e9:.3f}']
        table.append(f'<tr data-region="{v["region"]}" data-crop="{v["crop"]}">'+''.join(f'<td>{escape(c)}</td>' for c in cells)+'</tr>')
    headers=['Region','Crop','Store mm','Bare ET / PET','Delivery efficiency','Water access','Crop ET coverage','Area ≥95% ET km²','Delivered km³','Delivery loss km³']
    downloads=' · '.join(f'<a href="{n}" download>{label}</a>' for n,label in [('plan.json','Declared protocol'),('results.json','All results'),('review.json','Independent review and replay'),('controls.json','Controls'),('fields.csv.gz','All field CSV rows (gzip)'),('fields.npz','Monthly fields (NPZ)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flood storage and winter crop water · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption,.note{{font-size:.9rem}}.status{{background:var(--plate);border-left:4px solid var(--accent);padding:12px 18px}}.table{{max-height:650px;overflow:auto;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}td,th{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../flood_basin/">Gauge timing audit</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Floodwater must survive until the crop needs it</h1><p class="status">Finite field storage is now coupled to the conserved river ledger. All 96 development scenarios are retained. Storage capacities are sensitivity limits; none has been calibrated or adopted for the settlement map.</p></header>
<section><h2>The missing water is seasonal</h2><p>The fixed November–March crop cannot use a summer flood merely because that water passed nearby. Water must be diverted once, retained in a finite store, and survive evaporation. Upstream withdrawals and delivery losses consume the same river budget; fields sharing a river receive proportional shares of available delivery.</p>
<p>For Nile barley with bare-field evaporation equal to reference PET and loss-free delivery, 100 mm storage covers about 10% of crop demand, 300 mm about 70%, and 600 mm all demand. The rain-only comparison covers about 10%. This shows storage sensitivity, not evidence that historical soils held 600 mm.</p>
<figure><a href="storage_sweep.png" download><img src="storage_sweep.png" width="1760" height="1280" alt="All declared storage capacities for barley and wheat on Nile and Euphrates candidate fields. Solid flood-capture and dashed rain-only curves retain both bare-evaporation bounds; bands retain delivery efficiencies."></a><figcaption>Both regions use the same fixed calendar. All capacity, bare-evaporation, efficiency and no-capture cases remain in the table and downloads. Crop ET coverage measures water supply relative to potential evapotranspiration.</figcaption></figure></section>
<section><h2>Field water maps</h2><p>These maps show water coverage on the existing low-terrain candidate mask. Terrain is treated as test field area; farming and fallow shares are not used to infer actual cultivated area. Grey candidate cells have missing climate or fail the fixed crop's temperature/heat requirements.</p><figure><a href="field_water_maps.png" download><img src="field_water_maps.png" width="1920" height="1440" alt="Six maps show Nile and Lower Mesopotamia candidate terrain under 100, 300 and 600 mm storage, coloured by barley crop ET coverage. This is a water diagnostic, not settlement populations."></a><figcaption>Mapped illustration: bare ET = PET, delivery efficiency = 1, August–October flood capture. It selects no preferred storage capacity. Every source arc-minute cell is retained in its containing five-minute climate field with its actual area.</figcaption></figure></section>
<section><h2>All 96 scenarios</h2><p>“Area ≥95% ET” is area meeting a declared water-adequacy threshold in this scenario. It is not a calibrated irrigated area or a crop-yield prediction. River volumes are km³ per year.</p>
<div class="filters"><label>Region<select id="region"><option value="">Both regions</option><option value="nile">Nile</option><option value="mesopotamia_euphrates_only">Mesopotamia · Euphrates only</option></select></label><label>Crop<select id="crop"><option value="">Both crops</option><option value="barley">Barley</option><option value="wheat">Wheat</option></select></label></div><p id="count" role="status">96 scenarios</p>
<div class="table" tabindex="0" aria-label="All storage scenario results, horizontally scrollable"><table><thead><tr>{''.join('<th scope="col">'+h+'</th>' for h in headers)}</tr></thead><tbody>{''.join(table)}</tbody></table></div></section>
<section><h2>What these results can establish</h2><p>All 96 runs reach a repeating annual water balance from a paid zero-stock spin-up. Fifty-two controls pass. Independent terrain aggregation, raw climate checks and scalar field-by-field simulation verify {review['monthly_field_balances']:,} monthly field balances and {review['csv_rows']:,} CSV rows. Three fresh numeric files reproduce byte for byte. All 904 existing Earth atlas files remain unchanged.</p><p>{downloads}</p></section>
<section><h2>What remains before a map update</h2><p>Both regions are development diagnostics. The Nile source is the qualified pre-dam Aswan gauge, but modern WorldClim climate is from another period. Every accessible candidate field is assumed connected to one optimistic shared river pool. Negative terrain height above the nearest river is retained from the groundwork mask; actual flood access and drainage are unverified.</p><p>The Mesopotamian test supplies only Euphrates water; it omits the Tigris and cannot establish a complete regional budget or non-inflation result. Field storage, bare evaporation and delivery efficiency remain uncalibrated, and groundwater, return flows and realistic travel/storage infrastructure are absent. Indus remains unscored.</p><p>Next: qualify field storage and access, establish a shared Earth/fantasy river-flow input and independent test regions, then test the frozen harvest rule. The current settlement atlas, marketed share 0.3923 and whole-empire Egypt failure are unchanged.</p></section></main>
<script>function filter(){{let n=0;const region=document.getElementById('region').value,crop=document.getElementById('crop').value;for(const row of document.querySelectorAll('tbody tr')){{row.hidden=!!((region&&row.dataset.region!==region)||(crop&&row.dataset.crop!==crop));if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' scenarios';}}for(const id of ['region','crop'])document.getElementById(id).addEventListener('change',filter);</script></html>'''
    (PAGE/'index.html').write_text(html)
    evidence=ROOT/'atlases/earth_evidence/index.html';old=evidence.read_text();old=re.sub(r'<section id="flood-storage-feasibility">.*?</section>','',old,flags=re.S)
    panel='<section id="flood-storage-feasibility"><h2>Flood storage and winter crop water</h2><p>96 fixed-calendar development scenarios couple finite storage to conserved river withdrawals. Soil/field capacities remain uncalibrated. <a href="flood_storage/">Open field maps, matched rain-only controls and numeric downloads →</a></p></section>'
    evidence.write_text(old.replace('</header>','</header>'+panel,1))
    receipt=dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(evidence))
    (OUT/'publication.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
