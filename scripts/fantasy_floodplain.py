"""Port of the floodplain rule to the fantasy map (calibration/fantasy_floodplain_20261114/plan.json). Diagnostic:
derive() unchanged, then basin capacity blended and settlement fields recomputed. No atlas file is written."""
import copy, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest import floodplain as FP
from harvest.export import climate_arrays, derive, geometry, surface_months
from harvest.models import settlement_fields, core_term, lore_cores
from population.export import decode_harvest
from polity import fields as F, network as N
from scripts.land_people import analyse, NEED_KCAL
from scripts.vector_rivers import river_classes
from rotclimate.geography import source_layers, target_fullres
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/fantasy_floodplain_20261114/plan.json'; OUT = ROOT / 'output/fantasy_floodplain_20261114'; DATA = ROOT / 'atlases/earth_fit/data'


def meta_for(mode):
    original = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(original)
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'): meta[k] = original['corrected_climate'][k]
    return meta, (DATA / 'corrected' if mode == 'corrected' else DATA)


def basin_share(meta, shape):
    layers = source_layers(); land = layers['land']; H, W = land.shape; h, w = shape
    z = np.load(ROOT / meta['world']['terrain_file'])['z'].astype(float)
    original = np.asarray(Image.open(ROOT / 'data/source/original/rivers.png'))[..., 3] / 255.; _, nav = river_classes(original)
    Y, X = np.mgrid[:H, :W]
    nav_src = ndi.map_coordinates(nav.astype(float), [(Y + .5) * nav.shape[0] / H - .5, (X + .5) * nav.shape[1] / W - .5], order=0, mode='nearest') > .5
    cand = FP.candidate(land, np.where(land, z, 0.0), nav_src & land, meta['mi_per_px'] * 1.609344)
    block = lambda a: np.asarray(a, float).reshape(h, H // h, w, W // w).mean((1, 3))
    return block(cand) / np.maximum(block(land), 1e-12)


def run(mode):
    meta, folder = meta_for(mode); arrays = climate_arrays(folder, meta)
    year_days = float(json.loads((ROOT / 'atlases/earth_fit/params.json').read_text()).get('year_days', 365)) if (ROOT / 'atlases/earth_fit/params.json').exists() else 365.0
    fields, geo, names, _ = derive(meta, arrays, year_days); land = geo['land_fraction'] > 0; shape = land.shape
    hm, hf = decode_harvest(folder)
    control = float(np.max(np.abs(np.nan_to_num(fields['settlement_base']) - hf['settlement_base'])))   # derive reproduces the published field (quantised)
    cell = meta['width'] * meta['mi_per_px'] * 1.609344 / shape[1]
    climate = F.map_climate(DATA, meta, arrays, shape); landb = geo['land_fraction'] > .5
    biome = np.asarray(arrays['biome']); swamp = np.asarray(Image.fromarray((target_fullres() == 5).astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.Resampling.BOX)) > 127
    wd = dict(elev=np.asarray(arrays['elev'], float), land=landb, road=np.zeros(shape, bool), density=np.zeros(shape), cell_km=cell, biome=biome, swamp=swamp,
              tilt=meta['world']['tilt'], river=F.navigable_rivers(shape), **climate)
    st = N.statics(wd); cl = N.climate(wd, st)
    t, p, d, latitude = surface_months(meta, arrays)
    q, ok, flood_rain = FP.qualifying(landb, st['catchment'], cl['flow'], p)
    share = np.where(q & land, basin_share(meta, shape), 0.0)
    idx = share > 0
    ob, nb = analyse(t[:, idx], p[:, idx], latitude[idx], meta['world']['tilt'], 0, np.ones(int(idx.sum())), geo['arable'][idx], d[:, idx])
    unit = np.zeros(shape); unit[idx] = FP.basin_unit_capacity(ob, geo['arable'][idx], NEED_KCAL)
    crop0 = np.nan_to_num(fields['crop_capacity']); crop1 = np.where(idx, FP.blend(crop0, share, unit), crop0)
    # recompute the settlement tail of derive() with the blended crop capacity
    sf0 = settlement_fields(crop0[land], np.nan_to_num(fields['npp'])[land], biome[land], geo['arable'][land], geo['water_distance'][land], np.nan_to_num(fields['malaria'])[land])
    sf1 = settlement_fields(crop1[land], np.nan_to_num(fields['npp'])[land], biome[land], geo['arable'][land], geo['water_distance'][land], np.nan_to_num(fields['malaria'])[land])
    tail_control = float(np.max(np.abs(sf0['settlement_base'] - np.nan_to_num(fields['settlement_base'])[land])))
    base1 = np.zeros(shape); base1[land] = sf1['settlement_base']; base0 = np.nan_to_num(fields['settlement_base'])
    term = core_term(land, biome, np.asarray(arrays['elev'], float), cell, lore_cores(meta['width'], meta['height'], shape)); weight = geo['land_fraction'].astype(float)
    cored1 = base1 * term * np.sum(base1 * weight) / max(np.sum(base1 * term * weight), 1e-9)
    km2 = cell ** 2 * weight
    lab, n = ndi.label(ndi.binary_dilation(idx, iterations=3)); clusters = []
    for i in range(1, n + 1):
        m = (lab == i) & idx
        if m.any():
            r, c = np.nonzero(m); clusters.append(dict(row=float(r.mean()), col=float(c.mean()), basin_km2=float((share * km2)[m].sum()),
                crop_capacity_before=float((crop0 * km2)[m].sum()), crop_capacity_after=float((crop1 * km2)[m].sum()),
                settlement_base_before=float((base0 * km2)[m].sum()), settlement_base_after=float((base1 * km2)[m].sum())))
    clusters.sort(key=lambda c: -c['basin_km2'])
    np.savez_compressed(OUT / f'fields_{mode}.npz', share=share, unit=unit, crop_before=crop0, crop_after=crop1, base_before=base0, base_after=base1,
                        cored_after=cored1, qualifying=q, catchment=st['catchment'], flow=cl['flow'], flood_rain=flood_rain)
    last = {str(b): FP.last_of_longest_run(cl['flow'][:, b] > 1) for b in range(1, cl['flow'].shape[1])}
    return dict(mode=mode, published_control_max_abs=control, tail_control_max_abs=tail_control, basins=int(cl['flow'].shape[1] - 1),
        basins_timing_ok=[int(b) for b in np.flatnonzero(ok)], last_flood_month_after_solstice=last, qualifying_cells=int(idx.sum()),
        basin_km2=float((share * km2).sum()), crop_capacity_total_before=float((crop0 * km2).sum()), crop_capacity_total_after=float((crop1 * km2).sum()),
        settlement_base_total_before=float((base0 * km2).sum()), settlement_base_total_after=float((base1 * km2).sum()), clusters=clusters[:15])


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True); rows = {}
    for mode in ('corrected', 'raw'):
        rows[mode] = run(mode); print(mode, {k: v for k, v in rows[mode].items() if k not in ('clusters', 'last_flood_month_after_solstice')}, flush=True)
    write(OUT / 'results.json', dict(status='fantasy_floodplain_port_diagnostic', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), module_sha256=sha(ROOT / 'harvest/floodplain.py'), modes=rows))


if __name__ == '__main__':
    main()
