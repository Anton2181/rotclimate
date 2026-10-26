"""Verify portable-bundle hashes, research links and a fresh extracted launcher.

Standard library only, like the atlas launcher; no model/cache dependencies.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit
import zipfile


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ('src', 'href') and value:
                self.paths.append(value)


def verify(bundle):
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe portable path: '+name)
        manifest = json.loads(archive.read('manifest.json'))['sha256']
        if set(names) != set(manifest) | {'manifest.json', 'README.txt'}:
            raise ValueError('Archive and manifest contents differ')
        for name, expected in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('Portable asset checksum failed: '+name)
        checked = 0
        for name in ['atlases/index.html', 'atlases/climate_accuracy/index.html']:
            parser = Links(); parser.feed(archive.read(name).decode('utf-8'))
            for link in parser.paths:
                url = urlsplit(link)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path)))
                if url.path.endswith('/'):
                    target += '/index.html'
                if target not in manifest:
                    raise ValueError(f'Broken portable research link: {name} -> {link}')
                checked += 1
        with TemporaryDirectory(prefix='rotclimate-portable-') as destination:
            archive.extractall(destination)  # every member name validated above
            result = subprocess.run([sys.executable, str(Path(destination)/'scripts/serve_atlases.py'), '--check'],
                                    capture_output=True, text=True, check=True)
            for name in ['free_fit', 'earth_fit', 'whittaker_fit']:
                if name+':' not in result.stdout:
                    raise ValueError('Fresh launcher omitted an atlas: '+name)
    return dict(status='passed', archive_files=len(names), manifest_files=len(manifest),
                checked_links=checked, fresh_launcher='passed', launcher_output=result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.bundle)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
