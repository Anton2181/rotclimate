"""Publish completed process diagnostics without adopting the failed prototype."""
from pathlib import Path
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from PIL import Image
from local_benchmark_protocol import file_hash, write_json
from organize_climate_accuracy import organize


def main():
    diagnostic = ROOT / 'output/r42_rain_diagnosis_20261102'
    probe = ROOT / 'output/descent_continuity_20261102'
    destination = ROOT / 'atlases/climate_accuracy/data'
    d = json.loads((diagnostic / 'summary.json').read_text())
    p = json.loads((probe / 'summary.json').read_text())
    if not d.get('complete') or not p.get('complete') or set(d['regions']) != set(p['regions']):
        raise ValueError('All declared diagnostic/control/prototype cases must be complete')
    packets, rows = {}, []
    for name in d['regions']:
        dr, pr = d['regions'][name], p['regions'][name]
        if dr['status'] != 'passed' or pr['status'] != 'passed' or not pr['disabled_fields_byte_equal']:
            raise ValueError('Unqualified controls: ' + name)
        if dr['case_identity'] != pr['case_identity']:
            raise ValueError('Process and prototype case inputs differ')
        for label, folder, row in [('diagnostic', diagnostic, dr), ('prototype', probe, pr)]:
            source = folder / (name + '.npz')
            if file_hash(source) != row['packet_sha256']:
                raise ValueError('Changed raw packet: ' + str(source))
            filename = 'r42_processes_' + label + '_' + name + '.npz'
            shutil.copyfile(source, destination / filename)
            packets[filename] = row['packet_sha256']
        a, b = pr['modes']['reference'], pr['modes']['continuity']
        rows.append((name, a['rain']['loss'], b['rain']['loss'], 100 * (b['rain']['loss'] / a['rain']['loss'] - 1)))
    mean = lambda mode, part: sum((r['modes'][mode]['temperature_monthly_mae_c'] if part == 'T'
                                  else r['modes'][mode]['rain']['loss']) for r in p['regions'].values()) / len(rows)
    t = mean('continuity', 'T') / mean('reference', 'T')
    rain = mean('continuity', 'P') / mean('reference', 'P')
    figures = []
    for source, name, caption in [
        (diagnostic / 'seasonal_moisture_budget.png', 'r42_processes_budget.png',
         'Signed terms in the existing steady concentration-form column equation. Monsoon drying is already in column drying. This is not a global conservation or source-water-tracing result.'),
        (probe / 'monthly_rain_comparison.png', 'r42_processes_comparison.png',
         'The continuity hypothesis slightly improves India, worsens the desert, and leaves the main seasonal rainfall errors. All cases and regressions are retained.')]:
        shutil.copyfile(source, destination / name)
        with Image.open(source) as image:
            w, h = image.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}</figcaption></figure>')
    write_json(destination / 'r42_processes.json', dict(
        status='complete', adoption=False, ordinary_benchmarks_reproduced=True,
        prototype_combined_ratio=.5 * (t + rain), temperature_ratio=t, rain_ratio=rain,
        diagnostics=d, prototype=p, packets=packets,
        diagnostic_protocol=json.loads((diagnostic / 'protocol.json').read_text()),
        prototype_protocol=json.loads((probe / 'protocol.json').read_text()),
        publisher_sha256=file_hash(Path(__file__))))
    body = ''.join(f'<tr><td>{n.replace("_", " ")}</td><td>{a:.5f}</td><td>{b:.5f}</td><td>{change:+.2f}%</td></tr>' for n, a, b, change in rows)
    downloads = ''.join(f'<li>{n.replace("_", " ")}: <a href="data/r42_processes_diagnostic_{n}.npz">process fields</a> · <a href="data/r42_processes_prototype_{n}.npz">ordinary / disabled / enabled full fields</a></li>' for n, *_ in rows)
    section = f'''<!--r42-processes-start--><section aria-labelledby="r42-processes-h">
<h2 id="r42-processes-h">r42 rainfall processes and a failed continuity hypothesis</h2>
<p>The adopted raw Earth model is r42. Its reconstructed 49-region comparison is 3.72% better than r41, with regional regressions reported. These completed diagnostics investigate the remaining seasonal errors; the older r39 subsystem studies below retain their original baselines and scopes.</p>
<p><strong>The new prototype is not adopted: four-region combined error worsens {100 * (.5 * (t + rain) - 1):.2f}%.</strong> Temperature error changes {100 * (t - 1):+.2f}% and rain loss {100 * (rain - 1):+.2f}%. This is an aggregate decision, not a requirement that every region improve. No unseen validation set was evaluated.</p>
<p>All four process diagnostics reproduce ordinary r42 benchmark errors to 1e-10 on the complete scored land footprints. The copied experimental model, disabled, reproduces all eight full-domain output arrays exactly. All twelve ordinary/disabled/enabled integrations pass unchanged numerical checks. The live calibration and atlas release use unchanged production physics.</p>
{figures[0]}
<p>Tripolitania has a false summer rainy season (JJA 1.146 versus 0.007 mm/day observed); North India has deficient monsoon rain (2.623 versus 5.643). Manchuria receives too much modeled eddy moisture in winter while its summer remains too dry. Annual totals alone hide these differences.</p>
{figures[1]}
<div class="table"><table><caption>Same footprints and numerical checks; rain-loss regressions retained</caption><thead><tr><th>Region</th><th>r42 rain loss</th><th>Prototype</th><th>Change</th></tr></thead><tbody>{body}</tbody></table></div>
<p class="note">The prototype subtracts column-wind convergence from geometric dry-air descent. This is a kinematic hypothesis, not a solved three-dimensional mass/energy budget. Four reused development regions do not establish annual global accuracy or optimizer global optimality. No normal climate, biome, population or atlas field is adopted from this prototype.</p>
<p><a href="data/r42_processes.json" download>Protocols, source hashes, residuals and all results</a> · <a href="../../reports/RAIN_PROCESSES_20261102.md">Interpretation</a> · <a href="../../reports/R42_20261101.md">Adopted r42 and reconstructed references</a></p><ul>{downloads}</ul>
</section><!--r42-processes-end-->'''
    page = ROOT / 'atlases/climate_accuracy/index.html'
    html = re.sub(r'<!--r42-processes-start-->[\s\S]*?<!--r42-processes-end-->', '', page.read_text())
    overview = '''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r42</h2>
<p>On 49 development regions, reconstructed matched-input tests give a monthly temperature MAE of about <strong>1.88 °C</strong> and a <strong>3.72% lower combined temperature/rain error than r41</strong>. Regional regressions remain; this is not a global accuracy percentage. <a href="../../reports/R42_20261101.md">Release and reference-recovery evidence</a>.</p>
<p>The <a href="../earth_fit/">Earth atlas</a> identifies the profile currently served and distinguishes its raw simulation from Earth-trained statistical corrections. Physics adoption and atlas publication are separate. The free and Whittaker fits retain their own published profiles.</p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain the original r39 measurements and sample definitions. They do not report r42 city accuracy. The newer completed experiments follow under Experiments.</p><!--current-earth-overview-end-->'''
    marker = r'<!--current-earth-overview-start-->[\s\S]*?<!--current-earth-overview-end-->'
    if re.search(marker, html):
        html = re.sub(marker, overview, html)
    else:
        html, count = re.subn(r'<p>Temperature is closer than rainfall\.[\s\S]*?</p>', overview, html, count=1)
        if count != 1:
            raise ValueError('Unknown historical overview; refusing an ambiguous rewrite')
    html = html.replace('Updated 27 October 2026 · observed Earth climate normals',
                        'Updated 2 November 2026 · current results and historical benchmarks')
    html = html.replace('</main>', section + '\n</main>')
    html, studies = organize(html)
    page.write_text(html)
    write_json(diagnostic / 'publication.json', dict(status='passed', adoption=False, newest=studies[0],
               figures=2, raw_packets=len(packets), page_sha256=file_hash(page)))
    print('Published', studies[0], 'with', len(packets), 'verified raw packets')


if __name__ == '__main__':
    main()
