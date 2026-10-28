"""Publish the fixed stable-separation outcome with all baselines visible."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_divergent_thermal import verify
from local_benchmark_protocol import file_hash,write_json
from PIL import Image


def publish(out):
    evidence,result,_=verify(out);saved=json.loads((out/'analysis.json').read_text())
    if evidence!=json.loads((out/'scientific_verification.json').read_text()) or any(saved.get(k)!=v for k,v in result.items()):
        raise ValueError('Need independently recomputed matching stable-separation analysis')
    for source,key in [('scripts/analyze_divergent_thermal.py','analyzer_sha256'),('scripts/audit_separated_structure.py','thermal_auditor_sha256'),('scripts/verify_divergent_shear.py','shear_verifier_sha256')]:
        if file_hash(ROOT/source)!=saved[key]:raise ValueError('Changed analysis source')
    names=[('divergent_thermal_scorecard.png','Location and month-sensitive rainfall loss and temperature changes against original wind controls'),
        ('divergent_thermal_rainfall.png','All original, single-pattern and separated-profile seasonal rainfall curves for both ocean settings'),
        ('divergent_thermal_pressure_levels.png','All three circulation closures and reference at matched925 and700hPa pressure levels'),
        ('divergent_thermal_rain_maps.png','Observed, original, single-pattern and separated-profile rainfall maps on shared seasonal color scales'),
        ('divergent_thermal_temperature_structure.png','Hypsometric virtual temperature and native India horizontal thermal gradients for the separated profile')]
    if set(saved['images_sha256'])!={name for name,_ in names}:raise ValueError('Changed complete figure set')
    data=ROOT/'atlases/climate_accuracy/data';images=[]
    for name,alt in names:
        if file_hash(out/name)!=saved['images_sha256'][name]:raise ValueError('Changed figure')
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as source:w,h=source.size
        images.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>')
    prototype_path=ROOT/'output/baroclinic_mode_20261028/verification.json'
    prototype=json.loads(prototype_path.read_text())
    for source,sha in prototype['sources'].items():
        if file_hash(ROOT/source)!=sha:raise ValueError('Changed isolated dry-mode source')
    prototype_image=ROOT/'output/baroclinic_mode_20261028/baroclinic_heating_response.png'
    if prototype.get('actual_earth_integrations')!=0 or prototype.get('coupled_climate_connected') is not False or file_hash(prototype_image)!=prototype['image_sha256']:
        raise ValueError('Changed isolated prototype scope/image')
    shutil.copyfile(prototype_image,data/prototype_image.name)
    with Image.open(prototype_image) as image:w,h=image.size
    prototype_figure=f'<figure><a href="data/{prototype_image.name}"><img src="data/{prototype_image.name}" width="{w}" height="{h}" loading="lazy" alt="Isolated manufactured heating response with convergence and discrete modal energy balance; not an Earth climate map"></a></figure>'
    write_json(data/'divergent_thermal.json',dict(saved,baroclinic_prototype=prototype,publisher_sha256=file_hash(Path(__file__)),scientific_verification_sha256=file_hash(out/'scientific_verification.json')))
    passed=[base for base,s in saved['scores'].items() if s.get('process_gain')]
    status='Development process criterion met; no adoption' if passed else 'Rainfall criterion failed; no adoption'
    intro=[];rows=[];annual=[]
    for key,score in saved['scores'].items():
        if 'regional' not in score:raise ValueError('Need all regional outcomes')
        base=score['ocean'];pattern=score['thermal_pattern']
        intro.append(f'{base}/{pattern}: mean paired rain-loss ratio {score["mean_rain_loss_ratio"]:.3f}, temperature MAE change {score["mean_temperature_mae_change_C"]:+.3f}°C')
        for region,values in score['regional'].items():
            d=saved['regions'][region];previous=d[key]['previous_common_rain']['loss']/d[base+'_control']['rain']['loss']
            rows.append(f'<tr><td>{base}/{pattern}</td><td>{region.replace("_"," ")}</td><td>{previous:.3f}</td><td>{values["rain_loss_ratio"]:.3f}</td><td>{values["temperature_mae_change_C"]:+.3f}</td></tr>')
    for region,d in saved['regions'].items():
        values=[d['hydro_'+suffix]['rain']['sim_mean_annual_mm'] for suffix in ('control','single','thermal')]
        annual.append(f'<tr><td>{region.replace("_"," ")}</td>'+''.join(f'<td>{x:.0f}</td>' for x in values)+f'<td>{d["hydro_control"]["rain"]["obs_mean_annual_mm"]:.0f}</td></tr>')
    decision=('A qualifying result is development evidence only; test excluded regions, finer resolution and world transfer before any adoption.' if passed else
        'The divergence split also fails the rainfall criterion. Stop kinematic/profile variants and move to dynamically forced circulation and atmospheric energy equations before further broad fitting.')
    section=f'''<!--divergent-thermal-start--><section aria-labelledby="divergent-thermal-h"><h2 id="divergent-thermal-h">Divergent return and rotational thermal circulation</h2>
<p><strong>{status}.</strong> A structural test now retains the original lower wind and divergent upper return, then adds only the mass-balanced thermal component above. This addresses a manufactured failure of the previous common projection: at flat terrain and constant Coriolis, imposing nondivergent geostrophic shear can erase the lower convergence. The new closure retains that convergence while keeping exact dry-column continuity.</p>
<p>{'; '.join(intro)}. Both pre-existing temperature patterns are fixed; no new decay constant, region fit, observed wind forcing or rainfall-law adjustment is introduced. Acceptance remains mean paired rainfall loss ≤0.95 versus ORIGINAL winds and mean temperature MAE increase ≤0.25°C. All four ocean/pattern combinations and all regional regressions are reported. Loss ratios are not accuracy percentages.</p>
<div class="table"><table><caption>Original-wind baseline; previous common projection and new split compared separately</caption><thead><tr><th>Ocean/pattern</th><th>Region</th><th>Previous common rain ratio</th><th>Split rain ratio</th><th>Split temperature MAE change °C</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="table"><table><caption>Hydrostatic-half annual rain mm, historical scoring definition</caption><thead><tr><th>Region</th><th>Original</th><th>Split/single</th><th>Split/separated</th><th>Observed</th></tr></thead><tbody>{''.join(annual)}</tbody></table></div>
<p>Eighteen actual integrations comprise six exact original controls and twelve split cases.76 focused tests and two policy checks passed before the experiment. Three older toy climate modes remain bit-for-bit unchanged with the flag off. Actual upper flow is independently reconstructed from exported lower flow, the dry-mass projection and pressure-integrated thermal gradients. The full raw thermal shear is NOT imposed: the target is historical divergent return plus projected thermal rotation, with its departure from raw shear exposed.</p>
{''.join(images)}
<p>{decision} Normal Earth r39 and published world/biome/population climates remain unchanged.</p>
<p>An isolated dry baroclinic prototype now solves momentum and thermal-thickness adjustment. Nine analytic/conservation tests pass, including heating-driven lower convergence and a discrete energy identity. The manufactured periodic example below adds zero Earth integrations; it is not connected to the climate model. Open/terrain boundaries, physical heating and moisture coupling are prerequisites. <a href="../../reports/BAROCLINIC_MODE_20261028.md">Dry-mode equations, tests and limits</a>.</p>
{prototype_figure}
<p class="note">This is a kinematic decomposition, not a new momentum, diabatic-heating or atmospheric-energy solution. It retains the prior lower-convergence source and fixed observed cloud/remote-monsoon backgrounds. Both temperature profiles, the zonal EBM proxy, two-box winds and equatorial regularization have their earlier limitations. Reused development regions and sparse native footprints are not independent new validation. The thermal audit uses cached layer heights and a first-order humidity correction. No global optimum is claimed.</p>
<p><a href="data/divergent_thermal.json" download>Download divergent-return outcomes, monthly diagnostics and verification</a> · <a href="../../reports/DIVERGENT_THERMAL_20261028.md">Structural derivation, fixed experiment and results</a></p></section><!--divergent-thermal-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--divergent-thermal-start-->' in text:
        before,tail=text.split('<!--divergent-thermal-start-->',1);_,after=tail.split('<!--divergent-thermal-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_fixed_mechanism_test',process_support=passed,
        metadata_sha256=file_hash(data/'divergent_thermal.json'),images_sha256=saved['images_sha256'],publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
