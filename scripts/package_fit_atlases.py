"""Package the three active atlas variants with a local HTTP entry page.

Data remain external files: open the extracted bundle through an HTTP server,
not file://. The bundle includes the report, biome methods and source license.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['free_fit', 'earth_fit', 'whittaker_fit']
INSTRUCTIONS = '''Rotclimate: three climate fits

Extract this whole archive, then double-click start_atlases.command (macOS)
or start_atlases.bat (Windows), with Python 3 installed. Or run:

    python3 scripts/serve_atlases.py

The launcher opens your browser. Keep its terminal window open while browsing.

The free and Earth fits optimize the seasonal target zones. The separate
Whittaker fit optimizes the proposed strict target-to-biome crosswalk. All
three classify the mean climate over surroundings layouts 1, 2 and 3.
The report explains the scores, crosswalk assumptions and numerical checks.
These are simulated potential climates, not observed vegetation maps.
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    files = [ROOT/'atlases/index.html', ROOT/'reports/THREE_FIT_20261022.md',
             ROOT/'reports/WHITTAKER_TARGETS_20261022.md', ROOT/'docs/BIOMES.md',
             ROOT/'reports/CONTINUE_20261022.md', ROOT/'data/biome_target_crosswalk.json',
             ROOT/'scripts/serve_atlases.py', ROOT/'start_atlases.command', ROOT/'start_atlases.bat']
    evidence = ROOT/'output/three_fit_20261022'
    for name in ['search_comparison.png', 'biome_comparison.png', 'search_review.json', 'search_evaluations.json',
                 'search_review.csv', 'atlas_validation.json', 'publication.json',
                 'recovery_probe.json', 'earth_numerics_check.json', 'browser/browser_checks.json']:
        file = evidence/name
        if file.exists():
            files.append(file)
    files += sorted((ROOT/'calibration/three_fit_20261022').glob('**/*.json'))
    summaries = {}
    for name in NAMES:
        directory = ROOT/'atlases'/name
        summary = json.loads((directory/'summary.json').read_text())
        assert summary['observed_numerics']['all_checks_passed'], name
        summaries[name] = summary
        files += sorted(f for f in directory.rglob('*') if f.is_file())
    manifest = dict(atlases=summaries, sha256={
        str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in files:
            archive.write(file, str(file.relative_to(ROOT)))
        archive.writestr('README.txt', INSTRUCTIONS)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(args.out) as archive:
        assert archive.testzip() is None
    result = dict(file=str(args.out), bytes=args.out.stat().st_size,
                  sha256=hashlib.sha256(args.out.read_bytes()).hexdigest(),
                  files=len(files)+2, integrity='passed')
    args.out.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
