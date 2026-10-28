"""Publish the fixed stable-separation outcome with all baselines visible."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_separated_thermal import verify
from local_benchmark_protocol import file_hash,write_json
from PIL import Image


def publish(out):
    evidence,result,_=verify(out);saved=json.loads((out/'analysis.json').read_text())
    if evidence!=json.loads((out/'scientific_verification.json').read_text()) or any(saved.get(k)!=v for k,v in result.items()):
        raise ValueError('Need independently recomputed matching stable-separation analysis')
    for source,key in [('scripts/analyze_separated_thermal.py','analyzer_sha256'),('scripts/audit_separated_structure.py','thermal_auditor_sha256'),('scripts/verify_separated_shear.py','shear_verifier_sha256')]:
        if file_hash(ROOT/source)!=saved[key]:raise ValueError('Changed analysis source')
    names=[('separated_thermal_scorecard.png','Location and month-sensitive rainfall loss and temperature changes against original wind controls'),
        ('separated_thermal_rainfall.png','All original, single-pattern and separated-profile seasonal rainfall curves for both ocean settings'),
        ('separated_thermal_pressure_levels.png','All three circulation closures and reference at matched925 and700hPa pressure levels'),
        ('separated_thermal_rain_maps.png','Observed, original, single-pattern and separated-profile rainfall maps on shared seasonal color scales'),
        ('separated_thermal_temperature_structure.png','Hypsometric virtual temperature and native India horizontal thermal gradients for the separated profile')]
    if set(saved['images_sha256'])!={name for name,_ in names}:raise ValueError('Changed complete figure set')
    data=ROOT/'atlases/climate_accuracy/data';images=[]
    for name,alt in names:
        if file_hash(out/name)!=saved['images_sha256'][name]:raise ValueError('Changed figure')
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as source:w,h=source.size
        images.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>')
    write_json(data/'separated_thermal.json',dict(saved,publisher_sha256=file_hash(Path(__file__)),scientific_verification_sha256=file_hash(out/'scientific_verification.json')))
    passed=[base for base,s in saved['scores'].items() if s.get('process_gain')]
    status='Development process criterion met; no adoption' if passed else 'Rainfall criterion failed; no adoption'
    intro=[];rows=[];annual=[]
    for base,score in saved['scores'].items():
        if 'regional' not in score:raise ValueError('Need all regional outcomes for publication')
        intro.append(f'{base}: mean paired rainfall-loss ratio {score["mean_rain_loss_ratio"]:.3f}, mean temperature MAE change {score["mean_temperature_mae_change_C"]:+.3f}°C')
        for region,values in score['regional'].items():
            d=saved['regions'][region];single=d[base+'_single']['rain']['loss']/d[base+'_control']['rain']['loss']
            rows.append(f'<tr><td>{base}</td><td>{region.replace("_"," ")}</td><td>{single:.3f}</td><td>{values["rain_loss_ratio"]:.3f}</td><td>{values["temperature_mae_change_C"]:+.3f}</td></tr>')
            if base=='hydro':
                values=[d['hydro_'+suffix]['rain']['sim_mean_annual_mm'] for suffix in ('control','single','thermal')]
                annual.append(f'<tr><td>{region.replace("_"," ")}</td>'+''.join(f'<td>{x:.0f}</td>' for x in values)+f'<td>{d["hydro_control"]["rain"]["obs_mean_annual_mm"]:.0f}</td></tr>')
    decision=('A qualifying result is development evidence only; test excluded regions, finer resolution and world transfer before any adoption.' if passed else
        'This is the second failed thermal/shear hypothesis. Stop adjusting these profile shapes and reassess how atmospheric energy and circulation are represented before more broad fitting.')
    section=f'''<!--separated-thermal-start--><section aria-labelledby="separated-thermal-h"><h2 id="separated-thermal-h">Stable separation of surface and atmospheric temperature patterns</h2>
<p><strong>{status}.</strong> The new fixed profile lets modeled near-surface land/ocean anomalies weaken with height toward the existing modeled zonal background. It uses no observed wind or temperature forcing for this law and no regional fit. A state-dependent decay bound guarantees that its prescribed dry lapse does not exceed g/cp; it does not claim solved atmospheric energy or convective adjustment.</p>
<p>{'; '.join(intro)}. The precommitted criterion requires a mean paired rainfall-loss ratio ≤0.95 versus the ORIGINAL wind closure and mean temperature MAE increase ≤0.25°C. Lower is better; loss ratios are not percentage accuracy estimates. All regional gains and regressions remain visible, with no individual rain-score veto. The failed single-pattern closure is context, not the acceptance baseline.</p>
<div class="table"><table><caption>Both candidate patterns versus original winds; identical fixed ocean settings and location/month-sensitive rainfall loss</caption><thead><tr><th>Ocean</th><th>Region</th><th>Single-pattern rain ratio</th><th>Separated rain ratio</th><th>Separated temperature MAE change °C</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="table"><table><caption>Annual rainfall mm — hydrostatic-half ocean setting, original historical scoring definition</caption><thead><tr><th>Region</th><th>Original winds</th><th>Single pattern</th><th>Separated</th><th>Observed</th></tr></thead><tbody>{''.join(annual)}</tbody></table></div>
<p>Eighteen actual integrations compare three northern development regions, two fixed ocean settings and three wind modes. The twelve historical controls must reproduce both earlier climate modes exactly.71 focused tests covered stability, hydrostatic lapse, pressure gradients, independent quadrature, floor crossings, terrain invariance, parameter partition and coupled conservation. Default-off toy states remain bit-for-bit identical. Actual step certificates, independently reconstructed shear, water equations and reference footprints are included in the download.</p>
{''.join(images)}
<p>{decision} The normal atlases retain their adopted climates; this experimental study does not replace Earth r39 or published world, biome or population fields.</p>
<p class="note">The background is a zonal EBM temperature proxy interpreted at101325Pa, not a separately solved free atmosphere. Both thermal references are smoothed at500km; the nominal anomaly depth derives from the existing lower dry-mass layer, and a warm-anomaly bound enforces dry static stability. This leaves energy, momentum, conditional moist instability, two-box winds and equatorial regularization as model limitations. Existing observed cloud/remote-monsoon backgrounds remain fixed. The same development regions and sparse native masks are reused; inferred virtual temperatures use cached pressure-layer heights and a first-order humidity correction. No independent validation or global optimum is claimed.</p>
<p><a href="data/separated_thermal.json" download>Download all stable-separation outcomes, monthly fields, native diagnostics and verification</a> · <a href="../../reports/SEPARATED_THERMAL_20261028.md">Design, stability derivation, results and next step</a></p></section><!--separated-thermal-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--separated-thermal-start-->' in text:
        before,tail=text.split('<!--separated-thermal-start-->',1);_,after=tail.split('<!--separated-thermal-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_fixed_mechanism_test',process_support=passed,
        metadata_sha256=file_hash(data/'separated_thermal.json'),images_sha256=saved['images_sha256'],publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
