"""Check the tracked atlas site in a fresh clone with core.autocrlf=true.

    python3 scripts/check_windows_style_clone.py --receipt output/<step>/windows_checkout.json

Run after committing. Line-ending-only differences in unpinned text files are
expected; every release-pinned evidence file must be byte exact and the
standard-library launcher must verify the release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(receipt):
    if subprocess.check_output(['git', 'status', '--porcelain', '--', 'atlases'], cwd=ROOT).strip():
        raise SystemExit('Commit the atlas changes first')
    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT, text=True).strip()
    commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    work = Path(tempfile.mkdtemp(prefix='atlas-wincheck-')); clone = work / 'clone'
    try:
        subprocess.run(['git', 'clone', '-q', '--depth', '1', '--no-checkout', '-c', 'core.autocrlf=true',
                        '--branch', branch, ROOT.as_uri(), str(clone)], check=True)
        subprocess.run(['git', 'config', 'core.autocrlf', 'true'], cwd=clone, check=True)
        subprocess.run(['git', 'sparse-checkout', 'set', '--no-cone', '/atlases/', '/scripts/', '/reports/', '/data/', '/polity/',
                        '/rotclimate/', '/*.md', '/start_atlases.*', '/.gitattributes'], cwd=clone, check=True)
        subprocess.run(['git', 'checkout', '-q', branch], cwd=clone, check=True)
        files = subprocess.check_output(['git', 'ls-files', 'atlases'], cwd=ROOT, text=True).splitlines()
        exact, eol, changed = [], [], []
        for f in files:
            a, b = (clone / f).read_bytes(), (ROOT / f).read_bytes()
            (exact if a == b else eol if a.replace(b'\r\n', b'\n') == b.replace(b'\r\n', b'\n') else changed).append(f)
        release = json.loads((ROOT / 'atlases/release.json').read_text())
        pinned = [('atlases/earth_evidence/' + k, d) for k, d in release.get('earth_evidence_sha256', {}).items()]
        pinned_ok = sum(digest(clone / f) == d for f, d in pinned)
        out = subprocess.run(['python3', 'scripts/serve_atlases.py', '--check'], cwd=clone, capture_output=True, text=True).stdout
        line = [l for l in out.splitlines() if l.startswith('Atlas release')]
        ok = not changed and pinned_ok == len(pinned) and bool(line) and release['earth_physics'] in line[0]
        result = dict(status='passed' if ok else 'failed', commit=commit, git_autocrlf=True,
            scope='tracked atlas site under atlases/ in a fresh sparse clone with core.autocrlf=true, compared with this checkout; standard-library launcher --check',
            tracked_atlas_files=len(files), byte_exact_assets=len(exact), line_ending_only_text_files=len(eol), content_changed=changed,
            release_pinned_evidence_files=len(pinned), release_pinned_evidence_byte_exact=pinned_ok, launcher_release_line=line)
        Path(receipt).write_text(json.dumps(result, indent=2) + '\n')
        print(result['status'], len(exact), 'byte exact,', len(eol), 'line-ending only,', len(changed), 'changed;', pinned_ok, 'of', len(pinned), 'pinned;', line)
        if not ok:raise SystemExit(1)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--receipt', required=True); main(p.parse_args().receipt)
