"""Promote a verified coverage-constrained Whittaker atlas; preserve its predecessor."""
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from rotclimate.config import Params
from rotclimate.biome_targets import coverage_policy
from verify_atlas_export import verify
from build_atlas_variant import page
from build_fit_hub import main as build_hub


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output=ROOT/'output/whittaker_coverage_20261022';record=output/'publication.json'
    stage=ROOT/'atlases/whittaker_fit_next';active=ROOT/'atlases/whittaker_fit'
    if record.exists():
        old=json.loads(record.read_text())
        if (old.get('status')=='published' and sha(active/'data/atlas.bin')==old['climate_sha256']
                and sha(active/'data/harvest.bin')==old['harvest_sha256']):
            print('Coverage atlas already published.');return
        raise ValueError('A different publication record already exists')
    policy=coverage_policy();validation=verify(stage,True,policy['publication_outside_limit'])
    summary=json.loads((stage/'summary.json').read_text())
    assert summary['fit_objective']=='whittaker-covered'
    assert summary['whittaker']['strict']['score']>=policy['publication_minimum_strict_score']
    selected=output/('publication_params.json' if (output/'publication_params.json').exists() else 'selected_params.json')
    assert json.loads(json.dumps(asdict(Params.from_json(selected))))==json.loads(json.dumps(asdict(Params.from_json(stage/'params.json'))))
    provenance=json.loads((stage/'data/build_provenance.json').read_text());sim=provenance['simulation']
    assert sim['seeds']==[1,2,3] and sim['params']['downsample']==8
    assert all(sha(ROOT/'rotclimate'/f)==h for f,h in sim['sources'].items())
    assert all(sha(ROOT/'data/source'/f)==h for f,h in sim['map_inputs'].items())
    assert all(sha(ROOT/f)==h for f,h in provenance['export_sources'].items())
    harvest=json.loads((stage/'data/harvest_provenance.json').read_text())
    assert all(sha(ROOT/f)==h for f,h in harvest['inputs']['sources'].items())
    previous=json.loads((active/'summary.json').read_text())
    before_meta=json.loads((active/'data/atlas.json').read_text());after_meta=json.loads((stage/'data/atlas.json').read_text())
    before=before_meta['biomes'][0]['share'];after=after_meta['biomes'][0]['share']
    assert after<before
    backup=output/'previous_atlas/whittaker_fit';backup.parent.mkdir(exist_ok=True)
    assert not backup.exists()
    active.rename(backup)
    try:stage.rename(active)
    except Exception:
        backup.rename(active);raise
    pages_path=ROOT/'atlases/pages.json';pages=json.loads(pages_path.read_text())
    pages['whittaker_fit']['note']=(f'Fitted to the strict target-to-Whittaker crosswalk with a diagram-coverage guard. '
        f'{after:.2%} of source land remains outside the unchanged envelopes (previously {before:.2%}). '
        'Annual biomes do not guarantee summer drought or swamp hydrology. Climate averages surroundings layouts 1–3, '
        'with recorded linear, temperature and moisture convergence checks. Farming and population use low-input c.200 AD scenarios.')
    pages_path.write_text(json.dumps(pages,ensure_ascii=False,indent=1)+'\n')
    h=pages['whittaker_fit'];template=(ROOT/'atlas/index.html').read_text()
    (active/'index.html').write_text(page(template,h['title'],h['eyebrow'],h['lede'],h['note']))
    for file in ['climate-comparison.js','harvest.js']:shutil.copy(ROOT/'atlas'/file,active/file)
    build_hub()
    publication=dict(status='published',published_utc=datetime.now(timezone.utc).isoformat(),
        previous_summary=previous,summary=summary,native_choice=json.loads((output/'native_choice.json').read_text()),before_outside_share=before,after_outside_share=after,
        relative_outside_reduction=1-after/before,coverage_policy=policy,validation=validation,
        climate_sha256=sha(active/'data/atlas.bin'),harvest_sha256=sha(active/'data/harvest.bin'),
        selected_params_match=True,simulation_sources_match=True,map_inputs_match=True,export_sources_match=True,
        harvest_sources_match=True)
    record.write_text(json.dumps(publication,indent=2)+'\n')
    print(f'Published Whittaker atlas: outside land {before:.4%} -> {after:.4%}')


if __name__=='__main__':main()
