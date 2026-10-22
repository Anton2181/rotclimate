"""Serve the atlas files locally and open them in your browser (standard library only)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--no-browser', action='store_true')
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
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    except OSError:
        if args.port != 8000:
            raise
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    url = f'http://127.0.0.1:{server.server_address[1]}/{path}'
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
