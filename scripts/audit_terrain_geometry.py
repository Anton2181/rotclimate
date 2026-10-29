"""Static audit of omitted terrain pressure/depth; no climate integrations."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import rainfall_month_pilot as month
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,reference_geopotential,terrain_pressure_grid
from rotclimate.column_thermodynamics import G


def audit(out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True);literal=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';protocol=json.loads(literal.read_text())
    for name,digest in protocol['sources'].items():assert file_hash(ROOT/name)==digest,name
    records={};fields={};fig,axes=plt.subplots(3,3,figsize=(13,11))
    for row,region in enumerate(['north_india','mexico','pacific_nw']):
        case=next(c for c in protocol['cases'] if c['kind']=='prototype' and c['region']==region and c['initial_water']=='wet' and c['primary']);plan=json.loads((ROOT/case['plan']).read_text());base,a,model,*_=month.prepare(plan,region)
        sea=a['archived_surface_temperature_c']+273.15+plan['source_lapse_k_m']*a['elevation'];p0=float(model.column.edges_pa[0]);ptop=float(model.column.edges_pa[-1]);ps=surface_pressure_from_height(a['elevation'],sea,sea_level_pressure_pa=p0,lapse_k_m=plan['source_lapse_k_m'])
        sigma=(model.column.edges_pa-ptop)/(p0-ptop);grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);phi=reference_geopotential(ps,sea,sea_level_pressure_pa=p0,lapse_k_m=plan['source_lapse_k_m']);np.testing.assert_allclose(phi,G*a['elevation'],rtol=1e-12,atol=1e-8)
        excess=(p0-ps)/(p0-ptop);mass=(p0-ptop)/G-grid.dry_mass_kg_m2.sum(0);np.testing.assert_allclose(mass,(p0-ps)/G,rtol=1e-11,atol=1e-10)
        ref=load(ROOT/protocol['reference_footprints'][region]);mask=ref['score_mask'];area=ref['valid_area_km2'][mask];land=a['land'].astype(bool)
        records[region]=dict(reference_bottom_pressure_pa=p0,top_pressure_pa=ptop,reference_lapse_k_m=plan['source_lapse_k_m'],land_height_min_m=float(a['elevation'][land].min()),land_height_max_m=float(a['elevation'][land].max()),land_pressure_min_pa=float(ps[land].min()),land_pressure_max_pa=float(ps[land].max()),maximum_analytic_hydrostatic_height_residual_m=float(abs(phi/G-a['elevation']).max()),maximum_column_mass_residual_kg_m2=float(abs(grid.dry_mass_kg_m2.sum(0)-(ps-ptop)/G).max()),fixed_score_footprints=dict(area_weighted_mean_elevation_m=float(np.average(a['elevation'][mask],weights=area)),area_weighted_reference_pressure_pa=float(np.average(ps[mask],weights=area)),area_weighted_flat_column_mass_excess_fraction=float(np.average(excess[mask],weights=area)),maximum_flat_column_mass_excess_fraction=float(excess[mask].max())),plan_sha256=file_hash(ROOT/case['plan']))
        for key,value in dict(latitude=a['latitude'],longitude=a['longitude'],land=land,elevation_m=a['elevation'],sea_level_temperature_k=sea,reference_surface_pressure_pa=ps,hybrid_edges_pa=grid.edges_pa,hybrid_dry_mass_kg_m2=grid.dry_mass_kg_m2,flat_column_mass_excess_fraction=excess,score_mask=mask).items():fields[region+'_'+key]=value
        for col,(value,title,unit) in enumerate([(a['elevation'],'Archived source elevation','m'),(ps/100,'Dry hydrostatic reference surface pressure','hPa'),(100*excess,'Flat-column mass excess / flat model depth','%')]):
            ax=axes[row,col];image=ax.pcolormesh(a['longitude'],a['latitude'],value,shading='nearest',cmap=['terrain','viridis','magma'][col]);coast=ax.contour(a['longitude'],a['latitude'],land.astype(float),levels=[.5],colors='#173948',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.7,foreground='white')]);ax.scatter(a['longitude'][mask],a['latitude'][mask],s=8,edgecolors='#111',facecolors='none',linewidths=.5);ax.set_title(region.replace('_',' ')+': '+title,fontsize=9);fig.colorbar(image,ax=ax,shrink=.75,label=unit);ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
    fig.suptitle('Terrain geometry omitted by the current flat-bottomed prototype',fontsize=14);fig.text(.5,.01,'Static dry reference from the same source heights/lapse and sea-level pressure • not observed surface pressure, a weather forecast, or an adopted mass correction',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'terrain_geometry.png',dpi=145);plt.close(fig)
    np.savez_compressed(out/'terrain_geometry.npz',**fields)
    result=dict(status='static_terrain_geometry_audit',actual_integrations_started=0,regions=records,monthly_protocol_sha256=file_hash(literal),geometry_source_sha256=file_hash(ROOT/'rotclimate/terrain_hydrostatics.py'),audit_source_sha256=file_hash(Path(__file__)),figure_sha256=file_hash(out/'terrain_geometry.png'),fields_sha256=file_hash(out/'terrain_geometry.npz'),physics_adoption=False,scope='Dry hydrostatic reference geometry only; no momentum/pressure-gradient or work-compatible terrain solver. Current flat prototype and active monthly forecasts are unchanged. Variable column mass cannot be inserted into the current operators without rebuilding dry-mass continuity, pressure work and boundary fluxes.')
    write_json(out/'verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audit(a.out)
