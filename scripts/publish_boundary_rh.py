"""Publish independently verified marine RH process evidence, not a climate."""
from pathlib import Path
import argparse
import html
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from PIL import Image
from local_benchmark_protocol import file_hash, write_json
from verify_boundary_rh import verify


def publish(out):
    fresh = verify(out)
    receipt = json.loads((out / 'scientific_verification.json').read_text())
    if fresh != receipt:
        raise ValueError('Need matching independent process verification')
    protocol = json.loads((out / 'protocol.json').read_text()); p = protocol['plan']
    review = json.loads((out / 'review.json').read_text())
    data = ROOT / 'atlases/climate_accuracy/data'
    picture = data / 'boundary_rh_profiles.png'
    shutil.copyfile(out / 'marine_rh_profiles.png', picture)
    native = {}
    with np.load(out / 'native_profiles.npz', allow_pickle=False) as arrays, np.load(ROOT / p['parent_directory'] / 'native_profiles.npz', allow_pickle=False) as parent:
        for region in p['regions']:
            native[region] = {key: arrays[region + '_' + key].tolist() for key in [
                'native_area_km2', 'month_days', 'native_latitude', 'native_longitude',
                'native_flat_indices', 'pressure_hpa', 'observed_specific_humidity_kg_kg']}
            native[region]['environmental_6_specific_saturation_kg_kg'] = parent[region + '_environmental_6_specific_saturation_kg_kg'].tolist()
            native[region]['observed_925hpa_temperature_c'] = parent[region + '_observed_temperature_c'][:, 0].tolist()
    metadata = dict(review, plan=p, native_inputs=native,
                    scientific_verification=receipt, scientific_verification_sha256=file_hash(out / 'scientific_verification.json'),
                    source_protocol_sha256=file_hash(out / 'protocol.json'), source_review_sha256=file_hash(out / 'review.json'),
                    source_native_arrays_sha256=file_hash(out / 'native_profiles.npz'), images_sha256={picture.name: file_hash(picture)},
                    publisher_sha256=file_hash(Path(__file__)))
    write_json(data / 'boundary_rh.json', metadata)
    rows = []
    for name, score in review['reviews'].items():
        rows.append(f'<tr><td>{name}</td><td>{score["objective"]:.5f}</td><td>{score["mean_combined"]:.5f}</td><td>{score["worst_region"]:.5f}</td><td>{score["mean_shape_mae"]:.5f}</td><td>{"Reference support only" if score["supports_separately_declared_coupled_pilot"] else "No"}</td></tr>')
    regional = []
    for region, row in review['regions'].items():
        for name, value in row['profiles'].items():
            regional.append(f'<tr><td>{region.replace("_", " ")}</td><td>{name}</td><td>{value["water_mae_mm"]:.3f}</td><td>{value["shape_mae"]:.5f}</td><td>{review["reviews"][name]["regional"][region]["combined"]:.5f}</td></tr>')
    with Image.open(picture) as source:
        width, height = source.size
    section = f'''<!--boundary-rh-start--><section aria-labelledby="boundary-rh-h"><h2 id="boundary-rh-h">Pressure-dependent marine humidity: a process test</h2>
<p>Three fixed relative-humidity shapes share the same environmental 6 K/km temperature profile, observed 925 hPa temperature anchor, and 27 cached native ocean footprints. Actual humidity is withheld from construction. This comparison adds <strong>zero climate integrations</strong> and changes no running or adopted climate.</p>
<p>The half-strength pressure taper lowers the mean combined reference error by about 10.5% and mean humidity-shape MAE by about 20%. It strongly improves Iberia while the combined metric worsens at PNW and California. The full classical taper performs poorly overall. Average gains with regional regressions remain visible; neither result establishes a coupled rainfall response.</p>
<figure><a href="data/{picture.name}"><img src="data/{picture.name}" width="{width}" height="{height}" loading="lazy" alt="All three fixed marine relative humidity profiles versus observed partial water and vertical shape on PNW, Iberia and California native footprints"></a></figure>
<div class="table"><table><caption>Reference-process comparison; baseline normalized to one</caption><thead><tr><th>Fixed RH shape</th><th>Objective</th><th>Mean combined</th><th>Worst region</th><th>Mean shape MAE</th><th>Separate coupled-pilot support</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="table"><table><caption>Every regional water/shape error, including regressions</caption><thead><tr><th>Native ocean sample</th><th>Shape</th><th>Partial-water MAE mm</th><th>Shape-ratio MAE</th><th>Combined / baseline</th></tr></thead><tbody>{''.join(regional)}</tbody></table></div>
<p>Surface RH is fixed at 0.77. The full pressure taper follows the tropospheric form in Manabe and Wetherald (1967), Eq. 2; the intermediate taper interpolates RH before integrating water. Total water is not renormalized. The uniform 0.77 baseline is a process comparator, not a reproduction of the calibrated current ocean target. The original paper's stratospheric floor and radiative-convective model are absent.</p>
<p class="note">These 4 PNW, 20 Iberian and 3 Californian coarse ocean footprints were used before. They are model-assisted 1981–2010 reanalysis, not independent new validation, global skill or a monsoon-land test. Each native/month ratio is formed before averaging. Means can conceal local error; all area/day-weighted metrics and inputs remain downloadable. Reference support permits only a separately declared coupled pilot, never humidity forcing or adoption.</p>
<p><a href="data/boundary_rh.json" download>Download all marine RH inputs, native metrics and process decisions</a> · <a href="../../reports/BOUNDARY_RH_20261028.md">Declaration, verification and limitations</a> · <a href="{html.escape(p['paper_source'])}">Primary paper</a></p></section><!--boundary-rh-end-->'''
    page = ROOT / 'atlases/climate_accuracy/index.html'; text = page.read_text()
    if '<!--boundary-rh-start-->' in text:
        before, tail = text.split('<!--boundary-rh-start-->', 1); _, after = tail.split('<!--boundary-rh-end-->', 1)
        text = before + section + after
    else:
        anchor = '<!--drying-ablation-start-->'
        if text.count(anchor) != 1:
            raise ValueError('Need one preceding completed experiment')
        text = text.replace(anchor, section + '\n' + anchor)
    page.write_text(text)
    write_json(out / 'publication.json', dict(status='published_reference_only', page_sha256=file_hash(page),
               metadata_sha256=file_hash(data / 'boundary_rh.json'), publisher_sha256=file_hash(Path(__file__)),
               climate_integrations=0, physics_or_atlas_adoption=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    publish(parser.parse_args().out.resolve())
