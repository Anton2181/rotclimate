"""Prepare only regional source rasters; keep large official ZIPs in RAM."""
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write

CACHE=ROOT/'data/cache/earth_population_extension_20261111'
CONFIG=ROOT/'calibration/earth_population_extension_20261111'
OUT=ROOT/'output/earth_population_extension_20261111'
LAT=(32.,48.);LON=(120.,134.)
ETOPO=('https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/'
       'ETOPO_2022_v1_60s_N90W180_surface.nc.dods')


def body(url,maximum,progress=False):
    with urllib.request.urlopen(url,timeout=45) as response:
        declared=response.headers.get('Content-Length')
        if declared and int(declared)>maximum:raise ValueError('Source response exceeds declared bound')
        chunks=[];n=0
        while True:
            chunk=response.read(min(8*1024**2,maximum+1-n))
            if not chunk:break
            chunks.append(chunk);n+=len(chunk)
            if n>maximum:raise ValueError('Source stream exceeds declared bound')
            if progress and (len(chunks)%4==0):print('Downloaded',n//1024**2,'MiB in RAM',flush=True)
        if declared and n!=int(declared):raise ValueError('Truncated source response')
        return b''.join(chunks)


def climate(var):
    path=CACHE/f'worldclim_{var}.npz';receipt=CACHE/f'worldclim_{var}.json'
    if path.exists() and receipt.exists():
        metadata=json.loads(receipt.read_text())
        if metadata['regional_npz_sha256']!=sha(path):raise ValueError('Changed prepared source')
        return metadata
    local=ROOT/f'data/cache/worldclim/wc2.1_5m_{var}.zip'
    url=f'https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_5m_{var}.zip'
    print('Preparing',var,'from',str(local.relative_to(ROOT)) if local.exists() else url,flush=True)
    raw=local.read_bytes() if local.exists() else body(url,192*1024**2,True)
    rs=int((90-LAT[1])*12);re=int((90-LAT[0])*12);cs=int((LON[0]+180)*12);ce=int((LON[1]+180)*12)
    months=range(1,13) if var!='elev' else [None];fields=[];members=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for month in months:
            name=f'wc2.1_5m_{var}'+(f'_{month:02d}' if month is not None else '')+'.tif'
            info=archive.getinfo(name)
            if info.file_size>64*1024**2:raise ValueError('Unexpected TIFF member bound')
            payload=archive.read(info)
            with Image.open(io.BytesIO(payload)) as im:
                if im.size!=(4320,2160):raise ValueError('Unexpected WorldClim resolution')
                nd=im.tag_v2.get(42113);a=np.array(im.crop((cs,rs,ce,re)),np.float32)
                if nd is not None:a[a==float(str(nd).strip('\x00 '))]=np.nan
                a[a<-1e30]=np.nan
            fields.append(a);members.append(dict(name=name,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
    array=np.stack(fields) if var!='elev' else fields[0]
    np.savez_compressed(path,values=array,lat=LAT[1]-(np.arange(re-rs)+.5)/12,lon=LON[0]+(np.arange(ce-cs)+.5)/12)
    metadata=dict(source_url=url,local_archive_reused=local.exists(),archive_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest(),
        archive_members=members,regional_shape=list(array.shape),regional_npz_sha256=sha(path),regional_file=str(path.relative_to(ROOT)))
    write(receipt,metadata);return metadata


def etopo():
    path=CACHE/'etopo60.npz';receipt=CACHE/'etopo60.json'
    if path.exists() and receipt.exists():
        metadata=json.loads(receipt.read_text())
        if metadata['regional_npz_sha256']!=sha(path):raise ValueError('Changed ETOPO source')
        return metadata
    i0,i1=int((LAT[0]+90)*60),int((LAT[1]+90)*60)
    j0,j1=int((LON[0]+180)*60),int((LON[1]+180)*60)
    rows=[];sources=[]
    for first in range(i0,i1,120):
        last=min(first+120,i1);url=ETOPO+f'?z[{first}:1:{last-1}][{j0}:1:{j1-1}]'
        print('ETOPO regional rows',first-i0,'to',last-i0,flush=True)
        raw=body(url,2*1024**2)
        values,lat,lon=decode_etopo_grid(raw,last-first,j1-j0)
        if not np.allclose(lat,-90+(np.arange(first,last)+.5)/60,rtol=0,atol=1e-8):raise ValueError('Unexpected ETOPO latitude centres')
        if not np.allclose(lon,-180+(np.arange(j0,j1)+.5)/60,rtol=0,atol=1e-8):raise ValueError('Unexpected ETOPO longitude centres')
        rows.append(values);sources.append(dict(url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),shape=[last-first,j1-j0]))
    values=np.concatenate(rows)[::-1].astype(np.float32)
    np.savez_compressed(path,values=values,lat=LAT[1]-(np.arange(values.shape[0])+.5)/60,
        lon=LON[0]+(np.arange(values.shape[1])+.5)/60)
    metadata=dict(source_url=ETOPO,chunks=sources,regional_shape=list(values.shape),regional_npz_sha256=sha(path),regional_file=str(path.relative_to(ROOT)))
    write(receipt,metadata);return metadata


def decode_etopo_grid(raw,ny,nx):
    """Validate a DODS Grid's elevation and both coordinate arrays, not just z."""
    k=raw.index(b'Data:\n')+6;header=raw[:k].decode('ascii')
    for pattern in [rf'Float32\s+z\[lat\s*=\s*{ny}\]\[lon\s*=\s*{nx}\]',
                    rf'Float64\s+lat\[lat\s*=\s*{ny}\]',rf'Float64\s+lon\[lon\s*=\s*{nx}\]']:
        if not re.search(pattern,header):raise ValueError('Unexpected DODS grid schema')
    fields=[]
    for count,dtype in [(ny*nx,'>f4'),(ny,'>f8'),(nx,'>f8')]:
        if len(raw)<k+8:raise ValueError('Truncated DODS array counts')
        if not np.all(np.frombuffer(raw[k:k+8],'>u4')==count):raise ValueError('Unexpected DODS array counts')
        k+=8;nbytes=np.dtype(dtype).itemsize*count
        if len(raw)<k+nbytes:raise ValueError('Truncated DODS array')
        values=np.frombuffer(raw[k:k+nbytes],dtype)
        if not np.isfinite(values).all():raise ValueError('Nonfinite DODS values')
        fields.append(values);k+=nbytes
    if k!=len(raw):raise ValueError('Unexpected DODS trailing payload')
    return fields[0].reshape(ny,nx),fields[1],fields[2]


def main():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    methods=json.loads((CONFIG/'plan.json').read_text());assert methods['status']=='declared_before_regional_source_values_or_extension_scores'
    sources={}
    for var in ['elev','tavg','prec','tmin','tmax']:sources[var]=climate(var)
    sources['etopo60']=etopo()
    write(OUT/'sources.json',dict(status='regional_sources_prepared_no_model_or_overlap_scores',
        plan_sha256=sha(CONFIG/'plan.json'),producer_sha256=sha(Path(__file__)),bounds=dict(latitude=LAT,longitude=LON),
        sources=sources,global_archives_written_to_disk=False,raw_survey_rows_or_coordinates_read=False,
        physics_or_population_fields_computed=False))
    print('Regional sources ready;no extension fields or overlap scores computed.',flush=True)


if __name__=='__main__':main()
