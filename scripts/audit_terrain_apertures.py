"""Static common-pressure port and global mass-cancellation audit."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from monitor_extended_spinup import load
from local_benchmark_protocol import file_hash,write_json
from rotclimate.terrain_hydrostatics import terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures,mass_flux_divergence


def audit(source,out):
    source=source.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=True);meta=json.loads((source/'verification.json').read_text());assert file_hash(source/'terrain_geometry.npz')==meta['fields_sha256'];fields=load(source/'terrain_geometry.npz');records={};arrays={};rng=np.random.default_rng(260629)
    for region,record in meta['regions'].items():
        edges=fields[region+'_hybrid_edges_pa'];ps=fields[region+'_reference_surface_pressure_pa'];ptop=record['top_pressure_pa'];p0=record['reference_bottom_pressure_pa'];sigma=(edges[:,0,0]-ptop)/(ps[0,0]-ptop);sigma[0]=1.;sigma[-1]=0.;grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);np.testing.assert_allclose(grid.edges_pa,edges,atol=2e-11,rtol=0)
        ports=horizontal_apertures(grid);u=rng.normal(size=ports.east_kg_m2.shape);v=rng.normal(size=ports.south_kg_m2.shape);div=mass_flux_divergence(ports,u,v,224000.);relative=abs(div.sum())/max(abs(div).sum(),1e-100);assert relative<1e-14
        total=float(ports.east_kg_m2.sum()+ports.south_kg_m2.sum());diagonal=float(sum(ports.east_kg_m2[k,k].sum()+ports.south_kg_m2[k,k].sum() for k in range(len(edges)-1)));records[region]=dict(cross_level_fraction_of_open_pressure_mass=(total-diagonal)/total,maximum_layer_divergence_kg_m2_s=float(abs(div).max()),global_signed_divergence_kg_m2_s=float(div.sum()),relative_global_cancellation_error=float(relative),random_seed=260629,scope='Synthetic face velocities test pairwise mass cancellation only; not a wind forecast or a mass-balanced layer flow.')
        arrays.update({region+'_east_aperture_kg_m2':ports.east_kg_m2,region+'_south_aperture_kg_m2':ports.south_kg_m2,region+'_synthetic_layer_divergence':div})
    np.savez_compressed(out/'terrain_apertures.npz',**arrays)
    result=dict(status='static_terrain_ports_pass',regions=records,geometry_receipt_sha256=file_hash(source/'verification.json'),geometry_fields_sha256=meta['fields_sha256'],aperture_source_sha256=file_hash(ROOT/'rotclimate/terrain_apertures.py'),audit_source_sha256=file_hash(Path(__file__)),fields_sha256=file_hash(out/'terrain_apertures.npz'),actual_climate_integrations_started=0,physics_adoption=False,scope='Geometry and conservative interior flux incidence only. Compatible vertical flux, fixed-column mass constraint, momentum and pressure work remain required before weather integration.')
    write_json(out/'verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audit(a.source,a.out)
