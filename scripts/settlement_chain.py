"""Settlement chain runner (release 4 plan, WP0).

    settlement_chain.py <spec.json> verify|build [--stage NAME ...]

build: as verify, for a spec that changes the chain (its 'env' is passed to every stage); outputs are staged, not compared.

verify: runs every stage with all paths under the spec's output_root redirected to a staging folder
(output/chain_staging/<spec>), then compares each declared output byte for byte with the published copy.
Stages are existing scripts executed through scripts/exec_with.py with the spec's literal substitutions plus the
staging redirection; no script file is modified."""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = str(ROOT / '.venv/bin/python')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(spec_path, mode, only):
    spec = json.loads(Path(spec_path).read_text()); root = spec['output_root']
    stage_root = f'output/chain_staging/{Path(spec_path).stem}'; reach_root = stage_root + '/reach'
    if mode in ('verify', 'build') and not only: shutil.rmtree(ROOT / stage_root, ignore_errors=True)
    (ROOT / stage_root).mkdir(parents=True, exist_ok=True); report = []
    for st in spec['stages']:
        if only and st['name'] not in only: continue
        subs = [(a.replace('{root}', root).replace('{reach}', reach_root), b.replace('{root}', stage_root).replace('{reach}', reach_root)) for a, b in st['subs']]
        subs = [(a, b.replace(root, stage_root) if b.startswith(root) else b) for a, b in subs]
        src = (ROOT / st['script']).read_text(); extra = []
        for text in {root, 'output/capital_term_map_20261115', 'output/settlement_hierarchy_map_20261115'}:
            if text in src and all(a != text for a, _ in subs): extra.append((text, stage_root))
        args = [PY, '-I', str(ROOT / 'scripts/exec_with.py'), st['script']] + [f'{a}=>{b}' for a, b in subs + extra]
        print(f'== {st["name"]}: {st["script"]} ({len(subs) + len(extra)} substitutions)', flush=True)
        env = dict(os.environ, **{k: str(v) for k, v in spec.get('env', {}).items()})      # e.g. ROTCLIMATE_CONFLUENCE_K
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=env)
        if p.returncode: print(p.stdout[-2000:], p.stderr[-4000:]); raise SystemExit(f'stage {st["name"]} failed')
        rows = []
        for o in st.get('outputs', []):
            a, b = ROOT / root / o, ROOT / stage_root / o
            rows.append(dict(file=o, identical=a.is_file() and b.is_file() and sha(a) == sha(b), published=a.is_file(), staged=b.is_file()))
        for o in st.get('outputs_reach', []):
            first, rest = o.split('/', 1); pub = ROOT / st['published_reach_root'] / st['published_reach_map'][first] / rest; b = ROOT / reach_root / o
            rows.append(dict(file=o, identical=pub.is_file() and b.is_file() and sha(pub) == sha(b), published=pub.is_file(), staged=b.is_file()))
        report.append(dict(stage=st['name'], outputs=rows))
        for r in rows: print(('   same   ' if r['identical'] else '   DIFFER ') + r['file'], '' if r['identical'] else f"(published {r['published']}, staged {r['staged']})")
    out = ROOT / stage_root / 'verify.json'; out.write_text(json.dumps(dict(spec=spec_path, spec_sha256=sha(spec_path), runner_sha256=sha(__file__), stages=report), indent=1) + '\n')
    ok = all(r['identical'] for s in report for r in s['outputs'])
    if mode == 'build':
        print('BUILD done in', stage_root, '(differences from the published outputs are expected)'); return True
    print('VERIFY', 'PASSED' if ok else 'FAILED'); return ok


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('spec'); a.add_argument('mode', choices=['verify', 'build']); a.add_argument('--stage', nargs='*', default=[])
    g = a.parse_args(); sys.exit(0 if run(g.spec, g.mode, g.stage) else 1)
