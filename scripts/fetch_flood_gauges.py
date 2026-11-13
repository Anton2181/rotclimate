"""Fetch public gauge sources with pinned scientific input hashes.

PANGAEA HTML is the publisher's alternate representation of the same DOI;
its text endpoint was unavailable during this run. Changing publisher page
bytes requires a new source audit, not silently updating the expected digest.
"""
import hashlib
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/cache/flood_basin_seasonality_20261113'
SOURCES={
    'aswan.html':dict(url='https://doi.pangaea.de/10.1594/PANGAEA.218345?format=html',sha256='749bc87df120db3ce05d7cda943c7ba4c14c6be98df8064d29cca17e40abe9c6',citation='Vörösmarty, Fekete & Tucker (2004), Aswan Dam monthly discharge, PANGAEA.218345; RivDIS (1998), doi:10.3334/ORNLDAAC/199',license='CC-BY-3.0'),
    'hit.html':dict(url='https://doi.pangaea.de/10.1594/PANGAEA.218668?format=html',sha256='37c8744f1f14d5130cdfc46fdf7dcb14daf9eec9bb6e7a2b03f6a728dc249da5',citation='Vörösmarty, Fekete & Tucker (2004), Hit DS monthly discharge, PANGAEA.218668; RivDIS (1998), doi:10.3334/ORNLDAAC/199',license='CC-BY-3.0'),
    'dai.nc':dict(url='https://zenodo.org/records/17379716/files/coastal-stns-Vol-monthly.updated-Aug2025.nc?download=1',sha256='ae938f54c4915a9f970d5de8238ea4c88a5765eb7aaac25cfb1996e2973b4ae0',published_md5='9e0d54ba504a95f46b75a6be226f7c5b',citation='Dai (2025 update), doi:10.5281/zenodo.17379716; Dai & Trenberth (2002), Dai et al. (2009, 2025), as requested by dataset README',license='CC-BY-4.0, Zenodo record'),
    'dai_readme.txt':dict(url='https://zenodo.org/records/17379716/files/readme.txt?download=1',sha256='30b7822f10377b22d6816d1fba7c7a7b3f4228a5f0b3cc84b60646a5585c706e',citation='Dataset documentation, doi:10.5281/zenodo.17379716',license='CC-BY-4.0, Zenodo record')}


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    for name,spec in SOURCES.items():
        path=CACHE/name
        if not path.exists():
            request=urllib.request.Request(spec['url'],headers={'User-Agent':'rotclimate-source-audit/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:data=response.read()
            assert hashlib.sha256(data).hexdigest()==spec['sha256'],f'Publisher bytes changed: {name}; audit before reuse'
            path.write_bytes(data)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==spec['sha256'],name
        print(name,'verified')


if __name__=='__main__':main()
