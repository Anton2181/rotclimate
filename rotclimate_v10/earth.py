"""Explicit opt-in Earth inputs. Observed rain is kept outside model forcing.

WorldClim 2.1 (1970–2000) land temperature, rain and elevation; NOAA OISST
1971–2000 monthly SST. Use only public official HTTPS data, cached with hashes.
No rasterio/netCDF4 dependency: Pillow reads GeoTIFF and scipy reads classic NC.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import ssl
import urllib.request
import zipfile

import numpy as np
from PIL import Image
from scipy.io import netcdf_file
from scipy.ndimage import distance_transform_edt

from .core import Domain

WC = 'https://geodata.ucdavis.edu/climate/worldclim/2_1/base/'
SOURCES = {
    'wc2.1_10m_elev.zip': WC+'wc2.1_10m_elev.zip',
    'wc2.1_10m_tavg.zip': WC+'wc2.1_10m_tavg.zip',
    'wc2.1_10m_prec.zip': WC+'wc2.1_10m_prec.zip',
    'sst.ltm.1971-2000.nc': 'https://downloads.psl.noaa.gov/Projects/Datasets/noaa.oisst.v2/sst.ltm.1971-2000.nc',
}
# west, east, south, north; local Cartesian approximations, not global grids.
REGIONS = {'california': (-135.,-112.,30.,44.), 'iberia': (-20.,12.,28.,46.)}
SCHEMA = 1


def sha256(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path,value):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.part')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)


def atomic_npz(path,**arrays):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.part')
    with tmp.open('wb') as f:
        np.savez_compressed(f,**arrays)
    tmp.replace(path)


def validate_download(path):
    if path.name.endswith('.zip') or path.name.endswith('.zip.part'):
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise ValueError(f'Corrupt archive: {path}')
    else:
        with open(path,'rb') as f:
            if f.read(4) not in (b'CDF\x01',b'CDF\x02'):
                raise ValueError('SST must be classic NetCDF; the server returned an unsupported format.')


def fetch_raw(cache,progress=print):
    raw = Path(cache)/'raw';raw.mkdir(parents=True,exist_ok=True)
    context = ssl.create_default_context()
    # python.org macOS installations sometimes lack their default CA file.
    # Keep HTTPS verification on, adding the installed CA bundle when available.
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass
    provenance = {}
    for name,url in SOURCES.items():
        path = raw/name
        if not path.exists():
            progress(f'Downloading {name} from its official public source...')
            tmp = path.with_suffix(path.suffix+'.part')
            req = urllib.request.Request(url,headers={'User-Agent':'rotclimate-v10-research/1.0'})
            try:
                with urllib.request.urlopen(req,timeout=60,context=context) as source,tmp.open('wb') as dest:
                    size = 0
                    while True:
                        block = source.read(1024*1024)
                        if not block:break
                        size += len(block)
                        if size > 150*1024*1024:
                            raise ValueError(f'Unexpectedly large download: {name}')
                        dest.write(block)
                validate_download(tmp);tmp.replace(path)
            finally:
                tmp.unlink(missing_ok=True)
        validate_download(path)
        provenance[name] = {'url':url,'bytes':path.stat().st_size,'sha256':sha256(path)}
    atomic_json(Path(cache)/'sources.json',provenance)
    return provenance


def sample_tiff(image,longitude,latitude):
    """Nearest cell-centre sample of north-up PixelIsArea GeoTIFF, nodata -> NaN."""
    tags = image.tag_v2
    scale,tie = tags.get(33550),tags.get(33922)
    if scale is None or tie is None or len(tie) != 6 or len(scale) < 2 or tags.get(34264) is not None:
        raise ValueError('Need a north-up GeoTIFF with pixel scale and one tie point.')
    keys = tags.get(34735,())
    for i in range(4,len(keys),4):
        if keys[i] == 1024 and keys[i+1] == 0 and keys[i+3] != 2:
            raise ValueError('Need a geographic longitude/latitude raster, not projected coordinates.')
        if keys[i] == 1025 and keys[i+1] == 0 and keys[i+3] != 1:
            raise ValueError('Only PixelIsArea GeoTIFFs are supported.')
    sx,sy = scale[:2]
    if sx <= 0 or sy <= 0:
        raise ValueError('Invalid TIFF pixel scale.')
    # Floor is nearest to raster centres; it also gives the right half-open extent.
    col = np.floor((longitude-tie[3])/sx+tie[0]).astype(int)
    row = np.floor((tie[4]-latitude)/sy+tie[1]).astype(int)
    a = np.asarray(image,dtype=float)
    if a.ndim != 2:
        raise ValueError('Need a single-band geographic raster.')
    valid = (row>=0)&(row<a.shape[0])&(col>=0)&(col<a.shape[1])
    out = a[np.clip(row,0,a.shape[0]-1),np.clip(col,0,a.shape[1]-1)].copy()
    nodata = tags.get(42113)
    if nodata is not None:
        if isinstance(nodata,bytes):nodata = nodata.decode()
        value = float(str(nodata).strip('\x00 '))
        valid &= np.isfinite(out) if np.isnan(value) else out != value
    out[~valid|~np.isfinite(out)] = np.nan
    return out


def read_wc(raw,variable,longitude,latitude):
    name = f'wc2.1_10m_{variable}'
    with zipfile.ZipFile(Path(raw)/(name+'.zip')) as z:
        names = [name+'.tif'] if variable == 'elev' else [f'{name}_{m:02d}.tif' for m in range(1,13)]
        fields = []
        for member in names:
            with z.open(member) as stream,Image.open(stream) as image:
                fields.append(sample_tiff(image,longitude,latitude))
    return fields[0] if variable == 'elev' else np.stack(fields)


def nearest_fill(a):
    good = np.isfinite(a)
    if not good.any():
        raise ValueError('No valid data in regional forcing field.')
    indices = distance_transform_edt(~good,return_distances=False,return_indices=True)
    return a[tuple(indices)]


def read_sst(path,longitude,latitude):
    with netcdf_file(path,'r',mmap=False) as nc:
        variable = nc.variables['sst']
        raw = variable[:].copy()
        if raw.ndim != 3 or raw.shape[0] != 12 or getattr(variable,'dimensions',()) != ('time','lat','lon'):
            raise ValueError('Need twelve Jan–Dec SST fields on time,lat,lon axes.')
        valid = np.isfinite(raw)
        for key in ('missing_value','_FillValue'):
            if hasattr(variable,key):valid &= raw != getattr(variable,key)
        data = raw.astype(float)*float(getattr(variable,'scale_factor',1))+float(getattr(variable,'add_offset',0))
        data[~valid] = np.nan
        lat = nc.variables['lat'][:].copy();lon = nc.variables['lon'][:].copy()%360
        if (lat.ndim!=1 or lon.ndim!=1 or data.shape[1:]!=(len(lat),len(lon))
            or not np.isfinite(lat).all() or not np.isfinite(lon).all()):
            raise ValueError('Invalid SST coordinate axes.')
        units = getattr(variable,'units',b'').decode() if isinstance(getattr(variable,'units',b''),bytes) else variable.units
        if units.lower().strip() not in ('degc','c','degree_c','degrees_c','degrees c','degree_celsius','degrees_celsius'):
            raise ValueError(f'Unsupported SST units: {units!r}')
        # Also guard old products' unlabelled missing sentinels after unpacking.
        data[(data < -4.) | (data > 50.)] = np.nan
        # The file is small enough to fill ocean-mask holes once per monthly field.
        rows = abs(lat[:,None,None]-latitude).argmin(axis=0)
        delta = (lon[:,None,None]-longitude%360+180)%360-180
        cols = abs(delta).argmin(axis=0)
        return np.stack([nearest_fill(field)[rows,cols] for field in data])


@dataclass
class EarthCase:
    domain: Domain
    longitude: np.ndarray
    observed_rain_mm: np.ndarray
    score_mask: np.ndarray
    coast_distance_km: np.ndarray
    temperature_imputed: np.ndarray


def prepare_region(name,raw,spacing_km=60.):
    if name not in REGIONS or not np.isfinite(spacing_km) or not 30 <= spacing_km <= 200:
        raise ValueError('Choose a known region and spacing between 30 and 200 km.')
    west,east,south,north = REGIONS[name]
    dy = spacing_km*1000.;dx = dy
    dlat = dy/111195.;dlon = dx/(111195.*np.cos(np.deg2rad(.5*(south+north))))
    lons = np.arange(west+.5*dlon,east,dlon);lats = np.arange(north-.5*dlat,south,-dlat)
    longitude,latitude = np.meshgrid(lons,lats)
    elevation = read_wc(raw,'elev',longitude,latitude)
    land = np.isfinite(elevation)  # valid negative land elevations remain land
    tland = read_wc(raw,'tavg',longitude,latitude)
    observed = read_wc(raw,'prec',longitude,latitude)
    imputed = land & ~np.isfinite(tland).all(axis=0)
    sst = read_sst(Path(raw)/'sst.ltm.1971-2000.nc',longitude,latitude)
    # Fill only for forcing; imputed land cells are explicitly excluded from scoring.
    temperature = np.stack([np.where(land,nearest_fill(t),sea) for t,sea in zip(tland,sst)])
    mask = land & ~imputed & np.isfinite(observed).all(axis=0) & (observed>=0).all(axis=0)
    mask[:2,:] = False;mask[-2:,:] = False;mask[:,:2] = False;mask[:,-2:] = False
    coast = distance_transform_edt(land,sampling=(dy,dx))/1000.
    domain = Domain(name,land,np.where(land,elevation,0),latitude,temperature,dx,dy)
    domain.validate()
    if not mask.any() or not (~land).any():
        raise ValueError('Region must contain ocean and observed land away from the boundary.')
    return EarthCase(domain,longitude,observed,mask,coast,imputed)


def save_case(path,case):
    d = case.domain
    atomic_npz(path,land=d.land,elevation_m=d.elevation_m,latitude=d.latitude,
               temperature_c=d.temperature_c,dx=np.array(d.dx),dy=np.array(d.dy),
               longitude=case.longitude,observed_rain_mm=case.observed_rain_mm,
               score_mask=case.score_mask,coast_distance_km=case.coast_distance_km,
               temperature_imputed=case.temperature_imputed)


def load_case(path,name):
    with np.load(path,allow_pickle=False) as a:
        d = Domain(name,a['land'],a['elevation_m'],a['latitude'],a['temperature_c'],float(a['dx']),float(a['dy']))
        d.validate()
        case = EarthCase(d,a['longitude'],a['observed_rain_mm'],a['score_mask'],a['coast_distance_km'],a['temperature_imputed'])
        shape = d.land.shape
        if case.observed_rain_mm.shape != (12,)+shape or any(x.shape != shape for x in
            (case.longitude,case.score_mask,case.coast_distance_km,case.temperature_imputed)):
            raise ValueError('Incompatible prepared benchmark fields.')
        if case.score_mask.dtype != bool or not case.score_mask.any() or (case.score_mask & ~d.land).any():
            raise ValueError('Invalid benchmark scoring mask.')
        if not np.isfinite(case.observed_rain_mm[:,case.score_mask]).all() or (case.observed_rain_mm[:,case.score_mask]<0).any():
            raise ValueError('Scored reference rain must be finite and nonnegative.')
        return case
