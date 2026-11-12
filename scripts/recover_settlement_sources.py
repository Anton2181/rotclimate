"""Recover selected Han Earth-development ZIP members using verified HTTP ranges.

zipfile checks member CRCs. The receipt retains immutable file ID, API metadata
and member SHA256, not a claimed checksum verification of the whole 563MB ZIP.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/cache'


class RangeReader(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos+offset if whence == 1 else self.size+offset
        if self.pos < 0:
            raise ValueError('Negative seek')
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        n = min(n if n >= 0 else self.size-self.pos, self.size-self.pos)
        if n <= 0:
            return b''
        start = self.pos
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{start+n-1}'})
        with urllib.request.urlopen(req, timeout=45) as response:
            if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{start+n-1}/{self.size}':
                raise ValueError('Server did not honor the requested byte range')
            data = response.read(n+1)
        if len(data) != n:
            raise ValueError('Truncated or overlong range')
        self.pos += n
        return data


def han():
    api = 'https://api.figshare.com/v2/articles/30518417'
    with urllib.request.urlopen(api, timeout=30) as response:
        metadata = json.load(response)
    source = next(f for f in metadata['files'] if f['id'] == 59320670)
    archive = zipfile.ZipFile(RangeReader(source['download_url'], source['size']))
    out = CACHE / 'han_ad2/shp'; out.mkdir(parents=True, exist_ok=True)
    rows = []
    for member in archive.infolist():
        name = Path(member.filename).name
        if Path(name).stem not in ('CountyPointsWithPopulation','ResearchArea') or Path(name).suffix not in ('.shp','.shx','.dbf','.prj','.cpg'):
            continue
        data = archive.read(member)
        path = out/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Refusing to overwrite a different source: '+str(path))
        path.write_bytes(data)
        rows.append(dict(member=member.filename, bytes=len(data), crc32=member.CRC,
                         sha256=hashlib.sha256(data).hexdigest(), path=str(path.relative_to(ROOT))))
        print(name, len(data), flush=True)
    receipt = dict(api=api, article_title=metadata['title'], license=metadata.get('license'),
                   doi=metadata.get('doi'), file=source, members=rows, full_archive_checksum_verified=False)
    p=CACHE/'settlement_recovery_20261110';p.mkdir(exist_ok=True)
    (p/'han_sources.json').write_text(json.dumps(receipt, indent=2))


def rome():
    rows=[]
    with urllib.request.urlopen('https://zenodo.org/api/records/17122148',timeout=30) as r:
        record=json.load(r)
    road=next(f for f in record['files'] if f['key']=='itinere_roads.gpkg')
    targets=[(CACHE/'itinere/itinere_roads.gpkg',road['links']['self']),
             (CACHE/'hanson2016/cities.xlsx','https://oxrep.classics.ox.ac.uk/oxrep/docs/Hanson2016/Hanson2016_CitiesDatabase_OxREP.xlsx')]
    for path,url in targets:
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(url,timeout=45) as r:
                data=r.read()
            if path.suffix=='.gpkg':
                kind,digest=road['checksum'].split(':')
                if hashlib.new(kind,data).hexdigest()!=digest:
                    raise ValueError('Road source checksum mismatch')
            elif hashlib.sha256(data).hexdigest()!='5b9fc0195c3b5f2df71d6380174974215280cafd3bf5fa463fbf96969b549b6c':
                # Earlier oxrep.web.ox.ac.uk address returns 404 since 12 November 2026.
                raise ValueError('City workbook differs from the pinned source')
            path.write_bytes(data)
        rows.append(dict(path=str(path.relative_to(ROOT)),url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        print(path.name,path.stat().st_size,flush=True)
    url='https://raw.githubusercontent.com/Seshat-Global-History-Databank/cliopatria/5f433377139a6eeaeacbdc894b70f8805b72c8b5/cliopatria.geojson.zip'
    with urllib.request.urlopen(url,timeout=45) as r:
        archive=r.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        member=next(n for n in z.namelist() if n.endswith('.geojson'))
        full=json.loads(z.read(member))
    selected=[]
    for f in full['features']:
        p=f['properties'];years=[y for y in (2,117,150) if p['FromYear']<=y<=p['ToYear']]
        if years and f['geometry']:
            selected.append(dict(name=p['Name'],years=years,from_year=p['FromYear'],to_year=p['ToYear'],type=p.get('Type'),geometry=f['geometry']))
    path=CACHE/'cliopatria/geo/subset_ad2_117_150.json';path.parent.mkdir(parents=True,exist_ok=True)
    data=dict(source='Cliopatria v0.2.1, Seshat, CC BY4.0',years=[2,117,150],polities=selected)
    encoded=json.dumps(data).encode()
    if path.exists() and path.read_bytes()!=encoded:
        raise ValueError('Refusing to overwrite different Cliopatria subset')
    path.write_bytes(encoded)
    rows.append(dict(path=str(path.relative_to(ROOT)),url=url,archive_sha256=hashlib.sha256(archive).hexdigest(),
                     sha256=hashlib.sha256(encoded).hexdigest(),polities=len(selected)))
    out=CACHE/'settlement_recovery_20261110';out.mkdir(exist_ok=True)
    (out/'rome_sources.json').write_text(json.dumps(rows,indent=2))


if __name__ == '__main__':
    {'han':han,'rome':rome}[sys.argv[1]]()
