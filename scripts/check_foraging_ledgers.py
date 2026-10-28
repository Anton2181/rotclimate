"""Independently reconstruct final-year food/energy ledgers from atlas packets.

Uses saved start states, supplies, removal flows and endpoints, not the kernel's
reported maximum-residual certificates. All arithmetic is float64 after loading
the float32 packet. These ledgers describe the final simulated year, separately
from the final-window means used by the displayed foraging maps.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ATOL=1e-5
RTOL=8*np.finfo(np.float32).eps


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def balance(terms,*,label,atol=ATOL,rtol=RTOL):
    """Stored-rounding bound, scaled by the sum of absolute signed operands."""
    arrays=[np.asarray(a,dtype=float) for a in terms]
    if not arrays or not arrays[0].size or any(a.shape!=arrays[0].shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Invalid finite matching ledger operands: '+label)
    error=np.abs(sum(arrays));magnitude=sum(np.abs(a) for a in arrays)
    tolerance=atol+rtol*magnitude
    if np.any(error>tolerance):raise ValueError('Saved ledger does not close: '+label)
    return dict(status='passed',maximum_absolute_error=float(error.max()),
        maximum_tolerance_fraction=float((error/tolerance).max()),atol=atol,rtol_sum_absolute_operands=float(rtol))


def fat_bounds(change,start,end,catabolic,anabolic):
    """Check endpoints can realize nonnegative anabolic gain/catabolic loss.

    Reproduction is catabolic and is already included in change/end. Full daily
    gain/loss paths are not stored; this checks their necessary aggregate bounds.
    """
    if not 0<catabolic<anabolic:raise ValueError('Invalid asymmetric fat conversions')
    delta=end-start;checks={}
    for name,factor in [('catabolic_bound',catabolic),('anabolic_bound',anabolic)]:
        slack=change-factor*delta
        tolerance=ATOL+RTOL*(np.abs(change)+factor*(np.abs(end)+np.abs(start)))
        if np.any(slack < -tolerance):raise ValueError('Impossible annual fat-energy endpoints: '+name)
        checks[name]=dict(status='passed',minimum_slack_mj_person=float(slack.min()),
                         maximum_negative_slack_fraction=float(np.maximum(-slack,0).max()/max(float(tolerance.max()),ATOL)))
    return checks


def verify(atlas):
    atlas=Path(atlas);data=atlas/'data';path=data/'foraging.json'
    metadata=json.loads(path.read_text());binary=data/'foraging.bin';blob=binary.read_bytes()
    if sha(binary)!=metadata['binary_sha256']:raise ValueError('Changed foraging binary')
    expected=hashlib.sha256(json.dumps(metadata['inputs'],sort_keys=True).encode()).hexdigest()
    if expected!=metadata['fingerprint']:raise ValueError('Changed foraging input identity')
    if sha(data/'atlas.bin')!=metadata['original_climate_sha256']:raise ValueError('Changed climate packet')
    for name,digest in metadata['inputs']['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Changed scientific foraging source: '+name)
    arrays={};shape=tuple(metadata['shape']);last=0
    for name,spec in metadata['arrays'].items():
        dtype=np.dtype(spec['dtype']);offset=spec['offset_bytes'];count=int(np.prod(spec['shape']))
        stop=offset+count*dtype.itemsize
        if tuple(spec['shape'])!=shape or offset<last or offset%4 or stop>len(blob):raise ValueError('Changed packet layout')
        arrays[name]=np.frombuffer(blob,dtype=dtype,count=count,offset=offset).reshape(shape)
        last=stop
    if last!=len(blob):raise ValueError('Trailing data or incomplete packet')
    land=np.isfinite(arrays['land_fraction'])&(arrays['land_fraction']>0)
    def value(name):
        data=np.asarray(arrays[name][land],float)
        if not np.isfinite(data).all():raise ValueError('Nonfinite saved ledger: '+name)
        return data
    plant=balance([value('annual_start_plant_stock_kg_dm_km2'),value('annual_plant_supply_kg_dm_km2'),
        -value('annual_plant_decay_kg_dm_km2'),-value('annual_plant_harvest_kg_dm_km2'),-value('plant_stock_kg_dm_km2')],
        label='plant start + supply - decay - harvest - endpoint')
    meat=balance([value('annual_start_meat_stock_kg_dm_km2'),value('annual_meat_supply_kg_dm_km2'),
        -value('annual_meat_decay_kg_dm_km2'),-value('annual_meat_harvest_kg_dm_km2'),
        -value('annual_unused_prey_kg_dm_km2'),-value('meat_stock_kg_dm_km2')],
        label='meat start + supply - decay - harvest - annual unused prey - endpoint')
    intake=value('annual_intake_mj_person');expense=value('annual_expenditure_mj_person')
    reproduction=value('annual_reproduction_mj_person');change=value('annual_fat_energy_change_mj_person')
    energy=balance([intake,-expense,-reproduction,-change],
                   label='intake - expenditure - reproduction - integrated fat-energy change')
    parameters=metadata['parameters']['kernel_parameters']
    catabolic=parameters['fat_deficit_mj_kg'];anabolic=parameters['fat_surplus_mj_kg']
    physical=value('fat_kg');debt=value('energy_debt_mj');effective=value('effective_fat_kg')
    if np.any(physical<0)|np.any(debt<0)|np.any((physical>0)&(debt>0)):
        raise ValueError('Physical reserve and debt are not mutually exclusive nonnegative components')
    fat=balance([effective,-physical,debt/catabolic],label='effective reserve = physical fat - debt/catabolic energy')
    bounds=fat_bounds(intake-expense-reproduction,value('annual_start_effective_fat_kg'),effective,catabolic,anabolic)
    return dict(status='passed',atlas=str(atlas),fingerprint=metadata['fingerprint'],
        metadata_sha256=sha(path),binary_sha256=sha(binary),scientific_sources_verified=len(metadata['inputs']['sources']),
        land_cells=int(land.sum()),atol=ATOL,rtol_sum_absolute_operands=float(RTOL),
        tolerance_basis='8 float32 machine epsilons times sum of absolute stored operands, plus 1e-5 in each ledger unit',
        plant_mass_kg_dm_km2=plant,meat_mass_kg_dm_km2=meat,per_person_energy_mj=energy,
        physical_fat_and_energy_debt_kg=fat,asymmetric_fat_endpoint_bounds=bounds,
        scope='Final simulated year only. Food stocks/flows are per km2; energy is per representative person. Annual population changes make these per-capita ledgers distinct from a whole-population energy account. Final-window display means are not substituted into these terminal-year ledgers.',
        climate_integrations=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('atlases',nargs='+',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();results=[verify(path) for path in args.atlases]
    output=dict(status='passed',checks=results)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
