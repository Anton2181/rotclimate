"""Serve the atlas files locally and open them in your browser (standard library only)."""
import argparse
import hashlib
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import uuid
import webbrowser

PUBLISHED_BRANCH = 'claude/ecstatic-wozniak-rtrwd2'


def checkout_version(root):
    """Report this checkout, never an enclosing repository around a ZIP."""
    if not (root / '.git').exists():
        return None
    try:
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                           stderr=subprocess.DEVNULL, timeout=5).strip()
        return f'{git("rev-parse", "--abbrev-ref", "HEAD")} @ {git("rev-parse", "--short", "HEAD")}'
    except (OSError, subprocess.SubprocessError):
        return None


def release_version(root):
    """A release label is trusted only when it matches every atlas metadata file."""
    path = root / 'atlases/release.json'
    if not path.exists():
        return 'Unlabelled atlas snapshot; update the complete checkout or portable bundle.', None
    try:
        release = json.loads(path.read_text(encoding='utf-8'))
        hashes = release['metadata_sha256']
        if set(hashes) != {'free_fit', 'earth_fit', 'whittaker_fit'}:
            raise ValueError('Incomplete release manifest')
        for name, digest in hashes.items():
            actual = hashlib.sha256((root / 'atlases' / name / 'data/atlas.json').read_bytes()).hexdigest()
            if digest != actual:
                raise ValueError('Metadata changed')
        for name,digest in release.get('cereal_work_sha256',{}).items():
            if name not in hashes or hashlib.sha256((root/'atlases'/name/'data/farm_work.json').read_bytes()).hexdigest()!=digest:
                raise ValueError('Cereal-work map metadata changed')
        for name,digest in release.get('administrative_access_sha256',{}).items():
            if name not in hashes or hashlib.sha256((root/'atlases'/name/'data/administrative_access.json').read_bytes()).hexdigest()!=digest:
                raise ValueError('Administrative-access map metadata changed')
        for name,digest in release.get('administrative_hierarchy_sha256',{}).items():
            if name not in hashes or hashlib.sha256((root/'atlases'/name/'data/administrative_hierarchy.json').read_bytes()).hexdigest()!=digest:
                raise ValueError('Administrative-hierarchy metadata changed')
        for name,digest in release.get('pasture_sha256',{}).items():
            if name not in hashes or hashlib.sha256((root/'atlases'/name/'data/pasture.json').read_bytes()).hexdigest()!=digest:
                raise ValueError('Pasture-resource metadata changed')
        for name,digest in release.get('coverage_sha256',{}).items():
            if name not in hashes or hashlib.sha256((root/'atlases'/name/'data/coverage.json').read_bytes()).hexdigest()!=digest:
                raise ValueError('Coverage-audit metadata changed')
        hub = (root / 'atlases/index.html').read_text(encoding='utf-8').encode('utf-8')
        if hashlib.sha256(hub).hexdigest() != release['hub_sha256']:
            raise ValueError('Hub page changed')
        stamp = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        return f'Earth {release["earth_physics"]}; atlas snapshot {stamp}', stamp
    except (OSError, ValueError, KeyError, TypeError):
        return 'Release label does not match these local data; snapshot is unverified.', None


class AtlasHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=0, help='server port; default chooses a fresh available port')
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--check', action='store_true', help='show the served folder and dataset versions, then exit')
    ap.add_argument('--atlas', choices=['free_fit', 'earth_fit', 'whittaker_fit'])
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = next((p for p in (here, here.parent) if (p/'atlases/free_fit/index.html').exists()), None)
    if root is None:
        ap.error('Keep this launcher beside the atlases folder, or in the repository scripts folder.')
    path = 'atlases/'+args.atlas+'/' if args.atlas else (
        'atlases/' if (root/'atlases/index.html').exists() else 'atlases/free_fit/')
    if not (root/path/'index.html').exists():
        ap.error('That atlas has not been built yet.')
    names = [args.atlas] if args.atlas else ([name for name in ['free_fit', 'earth_fit', 'whittaker_fit']
            if (root/'atlases'/name/'index.html').exists()]
            if path == 'atlases/' else ['free_fit'])
    missing = [name for name in names if not all((root/'atlases'/name/'data'/file).exists()
               for file in ['atlas.json', 'atlas.bin'])]
    if missing:
        ap.error('Atlas data are missing for '+', '.join(missing)+'. Extract the complete portable atlas '
                 'bundle, including its data folders, or build the atlas first.')
    print(f'Atlas folder: {root}', flush=True)
    checkout = checkout_version(root)
    if checkout:
        print(f'Git checkout: {checkout}', flush=True)
        print(f'Published atlas branch: origin/{PUBLISHED_BRANCH}', flush=True)
    release, snapshot = release_version(root)
    print(f'Atlas release: {release}', flush=True)
    for name in names:
        with (root/'atlases'/name/'data/atlas.json').open(encoding='utf-8') as file:
            metadata = json.load(file)
        outside = next((b['share'] for b in metadata.get('biomes', []) if b['id'] == 0), None)
        coverage = f'{outside:.2%} outside the Whittaker diagram' if outside is not None else 'legacy data'
        work_path=root/'atlases'/name/'data/farm_work.json'
        work=json.loads(work_path.read_text(encoding='utf-8')) if work_path.exists() else None
        work_layers=work['packets']['raw']['layers'] if work else []
        admin_path=root/'atlases'/name/'data/administrative_access.json'
        admin=json.loads(admin_path.read_text(encoding='utf-8')) if admin_path.exists() else None
        admin_layers=admin['packets']['raw']['layers'] if admin else []
        hierarchy_path=root/'atlases'/name/'data/administrative_hierarchy.json'
        hierarchy=json.loads(hierarchy_path.read_text(encoding='utf-8')) if hierarchy_path.exists() else None
        hierarchy_layers=hierarchy['packets']['raw']['layers'] if hierarchy else []
        pasture_path=root/'atlases'/name/'data/pasture.json'
        pasture=json.loads(pasture_path.read_text(encoding='utf-8')) if pasture_path.exists() else None
        pasture_layers=pasture['packets']['raw']['layers'] if pasture else []
        audit_path=root/'atlases'/name/'data/coverage.json'
        audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else None
        audit_layers=audit['packets']['raw']['layers'] if audit else []
        print(f'  {name}: {coverage}; {len(metadata.get("layers", []))+len(work_layers)+len(admin_layers)+len(hierarchy_layers)+len(pasture_layers)+len(audit_layers)} map modes', flush=True)
        if work_layers:
            print('    Food and work: 6 views; partial cereal field-work scenarios',flush=True)
        if admin_layers:
            print(f'    Administration: 12 views; {admin["matched_centres"]}/{admin["listed_centres"]} seats located; seasonal access scenarios',flush=True)
        if hierarchy_layers:
            print(f'    Administrative links: 6 views; {len(hierarchy["registry"]["provinces"])} provincial capitals; directed seasonal reply times',flush=True)
        if pasture_layers:
            print('    Livelihoods: 6 views; worldwide forage, feed reserves and mapped water proximity',flush=True)
        if audit_layers:
            print(f'    Coverage audit: 6 views; {len(audit["packets"]["raw"]["actors"])} actors; source/seasonal uncertainty',flush=True)
        trade = metadata.get('reach', {}).get('trade', {})
        if trade.get('model'):
            layer = next((item for item in metadata.get('layers', []) if item['id'] == 'reach_trade'), {})
            views = len(layer.get('variants', {}).get('options', [])) or 1
            print(f'    Trade: {trade["model"]}; {views} views', flush=True)
    print('This launcher serves these local files; it does not download repository updates.', flush=True)
    if args.check:
        return
    handler = partial(AtlasHandler, directory=str(root))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    except OSError:
        if args.port != 8000:
            raise
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    url = f'http://127.0.0.1:{server.server_address[1]}/{path}'
    # Fresh origin and navigation URL avoid cached pages/assets from older
    # servers that used this computer's fixed localhost:8000 address.
    url += '?launch=' + uuid.uuid4().hex[:12]
    if snapshot:
        url += '&snapshot=' + snapshot
    print(f'Open {url}\nLeave this window open. Press Ctrl+C to stop.', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
