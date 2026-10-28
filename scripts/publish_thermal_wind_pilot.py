"""Publish the fixed wind-mechanism outcome, including its failed rain test."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_thermal_wind_pilot import verify
from local_benchmark_protocol import file_hash,write_json
from PIL import Image


def publish(out):
    evidence,result,_=verify(out);saved=json.loads((out/'analysis.json').read_text())
    if evidence!=json.loads((out/'scientific_verification.json').read_text()) or any(saved.get(k)!=v for k,v in result.items()):
        raise ValueError('Need independently recomputed matching pilot analysis')
    for file,key in [('scripts/analyze_thermal_wind_pilot.py','analyzer_sha256'),('scripts/audit_thermal_structure.py','thermal_auditor_sha256')]:
        if file_hash(ROOT/file)!=saved[key]:raise ValueError('Changed analysis source')
    figures=[('thermal_wind_scorecard.png','All three regional rainfall loss ratios and temperature changes under both fixed ocean settings'),
        ('thermal_wind_rainfall.png','Seasonal observed, control and new thermal wind rainfall curves for both ocean settings'),
        ('thermal_wind_pressure_levels.png','Matched925 and700hPa wind vectors with experimental and control simulations versus reference'),
        ('thermal_wind_rain_maps.png','Observed, old and thermal wind rainfall maps showing severe dry biases in the failed mechanism test'),
        ('thermal_wind_temperature_structure.png','Exploratory hypsometric layer temperature and India horizontal gradient comparisons')]
    if set(saved['images_sha256'])!={n for n,_ in figures}:raise ValueError('Changed complete figure set')
    data=ROOT/'atlases/climate_accuracy/data';images=[]
    for name,alt in figures:
        if file_hash(out/name)!=saved['images_sha256'][name]:raise ValueError('Changed diagnostic image')
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as image:w,h=image.size
        images.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>')
    write_json(data/'thermal_wind_pilot.json',dict(saved,publisher_sha256=file_hash(Path(__file__)),scientific_verification_sha256=file_hash(out/'scientific_verification.json')))
    rows=[]
    for base,score in saved['scores'].items():
        for region,values in score['regional'].items():
            rows.append(f'<tr><td>{base}</td><td>{region.replace("_"," ")}</td><td>{values["rain_loss_ratio"]:.3f}</td><td>{values["temperature_mae_change_C"]:+.3f}</td></tr>')
    section='''<!--thermal-wind-pilot-start--><section aria-labelledby="thermal-wind-pilot-h"><h2 id="thermal-wind-pilot-h">Thermal layer winds: a failed rainfall mechanism test</h2>
<p><strong>No rainfall gain; no adoption.</strong> A common-pressure hydrostatic temperature profile now drives an optional lower-to-upper thermal shear, with a shared dry-mass projection preserving that shear and exact column continuity. This default-off mechanism passed manufactured terrain/pressure tests and strict coupled ledgers, but the fixed development-region test worsened mean paired rainfall loss by47.2% with the legacy ocean and52.2% with the hydrostatic-half ocean. Mexico improves; India and PNW regress. A better native wind average is insufficient.</p>
<p>Twelve actual integrations completed: six historical controls reproduced every original climate field exactly, followed by six experimental cases. All 12 pass strict solver checks and the declared 80m/s branch-speed guard. The literal precommitted criterion required at least 5% lower mean rainfall loss and no more than0.25°C increase in mean temperature MAE. Both ocean settings fail the rain criterion; mean temperature MAE changes by−0.064°C and−0.080°C. This is a dimensionless location/month rainfall-loss comparison, not a percentage accuracy estimate.</p>
<div class="table"><table><caption>Paired regional outcomes; rainfall loss below1 improves, temperature change below0 improves</caption><thead><tr><th>Ocean</th><th>Region</th><th>Rainfall-loss ratio</th><th>Temperature MAE change °C</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>In the hydrostatic-half case, India's summer rain falls from 216 to 13 mm against 515 mm observed. Horizontal advective supply falls from 212 to 25 mm. PNW winter rain falls from 416 to 217 mm against 340 mm observed. Independent pressure quadrature reconstructs the actual exported shear within9×10<sup>−12</sup>m/s, alongside the water equations and donor fluxes. The failed result is physical-model behavior, not an unrecorded parameter search or a failed numerical solve.</p>
'''+''.join(images[:4])+'''
<p><strong>New structural clue, exploratory after outcomes:</strong> reanalysis pressure-layer thickness provides a hypsometric mean virtual temperature. On the same 11 India land footprints, a spatial plane estimates summer northward temperature gradients of +2.19 K/1000 km in 925–700 hPa but −0.54 K/1000 km in 700–300 hPa. The candidate profile gives +2.05 and +2.08respectively (three monthly estimates averaged equally). Its single common thermal pattern retains the wrong direction aloft. This sparse regional check supports investigating separate boundary-layer anomalies and a broader free-atmosphere thermal field; it does not establish a replacement or independently validate one.</p>
'''+images[4]+'''
<p class="note">The temperature check was added after seeing the failure, uses cached NCEP height reanalysis, and changes no acceptance rule or climate forcing. Model virtual temperature uses a first-order humidity correction. Native footprints remain sparse: 11 India land cells, 1 Mexico land cell, 3 PNW ocean cells and no valid PNW land sample. No spatial gradient is fitted with fewer than 4 cells. Reused development regions, mismatched reference periods, missing submonthly covariance, two-box winds, the fixed 10 degree Coriolis regularization and inherited observed cloud/remote-monsoon backgrounds limit interpretation. The common-height Tsl→101325Pa reference is a diagnostic approximation, not solved vertical energy.</p>
<p>The experiment adds 12 attempts / 12 strict passes. Cumulative counter: 1898 attempts, 1893 strict passes, 4 earlier failures and 1 earlier interruption. Earth r39 and all published world/biome/population fields remain unchanged. No broad recalibration or global-optimum claim follows.</p>
<p><a href="data/thermal_wind_pilot.json" download>Download all paired rainfall, temperature, wind, thermal-structure and verification results</a> · <a href="../../reports/THERMAL_WIND_PILOT_20261028.md">Declaration, results and next physical question</a> · <a href="../../reports/THERMAL_LAYER_PROTOTYPE_20261028.md">Operator derivation and prototype history</a></p></section><!--thermal-wind-pilot-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--thermal-wind-pilot-start-->' in text:
        before,tail=text.split('<!--thermal-wind-pilot-start-->',1);_,after=tail.split('<!--thermal-wind-pilot-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    # Clearly mark the previous prototype-only status as historical.
    text=text.replace('An isolated thermal-shear operator is now implemented and passes9 manufactured tests:', 'At this earlier milestone, an isolated thermal-shear operator passed9 manufactured tests:')
    text=text.replace('It is not connected to the coupled climate yet; constructing a common-pressure temperature gradient without terrain artifacts is the next prerequisite.', 'The later coupled pilot above now tests it with a common-pressure temperature construction; its rainfall outcome is reported separately.')
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_failed_mechanism_test',images_sha256=saved['images_sha256'],
        metadata_sha256=file_hash(data/'thermal_wind_pilot.json'),publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
