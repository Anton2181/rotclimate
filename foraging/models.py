"""Daily human energy and foraging dynamics after Zhu et al. (2021).

Independent implementation of the published FORGE human equations, accepting
explicit edible-resource inputs. It is not the coupled ORCHIDEE/herbivore model.
Resource forcing, plant decay and annual prey renewal are caller assumptions.
The manuscript gives crowding c=100 in its intake section and c=200 for its
standard calibrated configuration; the latter is used here and remains exposed.

Stocks/supplies use kg dry matter per km², populations persons per km², and
energy MJ per person. ``fat_kg`` is nonnegative physical reserve; a separate
energy debt preserves the original model's negative effective-fat starvation
indicator. No migration, agriculture, fishing or technological progress occurs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(**kwargs):
        return lambda fn: fn


@dataclass(frozen=True)
class ForagingParams:
    basal_mj_day: float = 8.37
    activity_mj_hour: float = 1.25
    food_mj_kg_dm: float = 9.8
    body_mass_kg: float = 50.0
    max_fat_kg: float = 15.0
    fat_deficit_mj_kg: float = 39.3
    fat_surplus_mj_kg: float = 54.6
    search_area_m2_hour: float = 4000.0
    maximum_efficiency: float = 1.0
    crowding: float = 200.0
    min_hours: float = 0.5
    max_hours: float = 8.0
    hours_step: float = 1.0
    initial_hours: float = 4.0
    carnivory_response: float = 2.5
    min_hunt_fraction: float = 0.05
    max_hunt_fraction: float = 0.95
    meat_fraction_floor: float = 0.1
    maximum_birth_rate: float = 0.1
    birth_sigmoid: float = 15.0
    starvation_sd_fat_fraction: float = 0.125
    background_mortality_year: float = 0.0125
    reproduction_mj_birth: float = 478.0
    population_floor_people_km2: float = 0.001
    # The paper supplies plant decay from ORCHIDEE, rather than a constant.
    # This explicit adapter assumption must be recorded with exported results.
    plant_decay_day: float = 0.02
    meat_decay_day: float = 0.0
    reset_meat_each_year: bool = True

    def validate(self):
        values = asdict(self)
        for name, value in values.items():
            if name == 'reset_meat_each_year':
                if not isinstance(value, (bool, np.bool_)):
                    raise ValueError('reset_meat_each_year must be boolean')
            elif not math.isfinite(value) or value < 0:
                raise ValueError('Need finite nonnegative parameter: '+name)
        for name in ('food_mj_kg_dm','body_mass_kg','max_fat_kg',
                     'fat_deficit_mj_kg','fat_surplus_mj_kg','search_area_m2_hour',
                     'maximum_efficiency','crowding','starvation_sd_fat_fraction'):
            if values[name] <= 0:
                raise ValueError('Need a positive parameter: '+name)
        if not (0 < self.min_hours <= self.initial_hours <= self.max_hours <= 24):
            raise ValueError('Need bounded initial and minimum/maximum foraging hours')
        if not (0 <= self.min_hunt_fraction <= self.max_hunt_fraction <= 1):
            raise ValueError('Need hunting fractions in [0,1]')
        if not (0 <= self.plant_decay_day <= 1 and 0 <= self.meat_decay_day <= 1):
            raise ValueError('Daily stock decay must be in [0,1]')
        if not 0 <= self.meat_fraction_floor <= 1:
            raise ValueError('Need meat_fraction_floor in [0,1]')
        if self.maximum_efficiency > 1:
            raise ValueError('Search efficiency must not exceed one')
        if self.maximum_birth_rate > 1 or self.background_mortality_year > 1:
            raise ValueError('Annual demographic rates must be in [0,1]')
        return self


SOURCE = {
    'paper': 'Zhu et al. (2021), Global hunter-gatherer population densities constrained by influence of seasonality on diet composition',
    'doi': 'https://doi.org/10.1038/s41559-021-01548-3',
    'scope': 'Independent published-equation human kernel with externally supplied edible food; not a reproduction of coupled global FORGE',
    'conventions': [
        'Crowding 200 is the manuscript standard configuration; its intake section also states 100.',
        'Annual reproductive energy uses catabolic 39.3 MJ/kg; the manuscript leaves the annual m convention ambiguous.',
        'Zero hunting/gathering benefits preserve the previous bounded hunting fraction.',
        'Food is removed only when consumed; any available intake above the fat ceiling stays in its resource pool.',
        'Effective fat may be negative for starvation risk; physical fat and energy debt are separately nonnegative.',
        'Unused annual prey is discarded when reset_meat_each_year=True, representing externally renewed annual prey budgets.',
        'Plant and meat turnover are explicit forcing assumptions, not universal published FORGE coefficients.',
    ],
}


def dry_matter_g_m2_to_kg_km2(value):
    """1 g/m² = 1,000 kg/km², without a carbon/dry-matter conversion."""
    value = np.asarray(value, dtype=float)
    if not np.isfinite(value).all() or (value < 0).any():
        raise ValueError('Need finite nonnegative dry matter')
    return value*1000.


def energy_to_fat_change(balance_mj, params=ForagingParams()):
    """Published asymmetric storage/catabolism conversion in kg per person."""
    params.validate()
    balance = np.asarray(balance_mj, float)
    if not np.isfinite(balance).all():
        raise ValueError('Need finite energy balances')
    return balance/np.where(balance >= 0, params.fat_surplus_mj_kg, params.fat_deficit_mj_kg)


def fat_components(effective_fat_kg, params=ForagingParams()):
    """Keep actual reserve and accumulated starvation indicator distinct."""
    params.validate()
    effective = np.asarray(effective_fat_kg, float)
    if not np.isfinite(effective).all():
        raise ValueError('Need finite effective fat')
    return np.maximum(effective,0.), np.maximum(-effective,0.)*params.fat_deficit_mj_kg


def demographic_rates(effective_fat_kg, params=ForagingParams()):
    """Annualized birth and starvation rates evaluated at one daily state."""
    params.validate()
    fat = np.asarray(effective_fat_kg,float)
    if not np.isfinite(fat).all():
        raise ValueError('Need finite effective fat')
    x = np.clip(params.birth_sigmoid*(fat/params.max_fat_kg-.5),-700.,700.)
    birth = params.maximum_birth_rate/(1.+np.exp(-x))
    # erf is provided by the standard library, avoiding a SciPy dependency.
    z = -fat/(params.starvation_sd_fat_fraction*params.max_fat_kg*math.sqrt(2.))
    starve = .5*np.asarray([math.erfc(-float(v)) for v in z.ravel()]).reshape(z.shape)
    return birth, starve


# Output rows from the compiled per-cell simulation.
_OUTPUT_NAMES = ('raw_density_people_km2','foraging_hours_day','meat_fraction',
    'scarcity_days_year','effective_fat_kg','annual_birth_rate','annual_starvation_rate',
    'annual_net_growth_rate','plant_stock_kg_dm_km2','meat_stock_kg_dm_km2',
    'annual_intake_mj_person','annual_expenditure_mj_person','annual_reproduction_mj_person',
    'annual_plant_harvest_kg_dm_km2','annual_meat_harvest_kg_dm_km2',
    'annual_plant_decay_kg_dm_km2','annual_meat_decay_kg_dm_km2',
    'annual_unused_prey_kg_dm_km2','maximum_resource_residual_kg_dm_km2',
    'maximum_energy_residual_mj_person','years_simulated','converged','floor_limited',
    'maximum_relative_resource_residual','maximum_relative_energy_residual',
    'annual_plant_supply_kg_dm_km2','annual_meat_supply_kg_dm_km2',
    'mean_density_people_km2','density_std_people_km2','density_min_people_km2',
    'density_max_people_km2','mean_foraging_hours_day','mean_meat_fraction',
    'mean_scarcity_days_year','mean_birth_rate','mean_starvation_rate',
    'mean_net_growth_rate','mean_effective_fat_kg','floor_year_fraction',
    'averaging_years_used','mean_supported_density_people_km2',
    'annual_start_plant_stock_kg_dm_km2','annual_start_meat_stock_kg_dm_km2',
    'annual_start_effective_fat_kg','annual_fat_energy_change_mj_person')


@njit(cache=True)
def _simulate_flat(plant, meat, packed, initial_p, initial_f, years, min_years, tolerance, stable_years, averaging_years):
    nday,ncell = plant.shape
    out = np.zeros((45,ncell))
    basal,activity,food,body,fmax,mminus,mplus,search,emax,crowd = packed[:10]
    hmin,hmax,hstep,hinit,kdiet,huntmin,huntmax,rmin = packed[10:18]
    bmax,bslope,fsigma,mb,repro,pfloor,pdecay,mdecay,reset = packed[18:27]
    for cell in range(ncell):
        p = initial_p[cell]; f = initial_f[cell]
        bv=0.; ba=0.; tf=hinit; prev_delta=0.; prev_meat=.5; prev_hunt=.5
        stable=0; converged=False
        history=np.zeros((averaging_years,10))
        maxmass=0.; maxenergy=0.; maxmassrel=0.; maxenergyrel=0.
        annual_plant_input=0.; annual_meat_input=0.
        for d in range(nday):
            annual_plant_input += plant[d,cell]
            annual_meat_input += meat[d,cell]
        for year in range(years):
            oldp=p; oldf=f; oldbv=bv; oldba=ba
            unused=ba if reset > .5 else 0.
            if reset > .5: ba=0.
            birth=0.; starve=0.; hours=0.; ia_sum=0.; iv_sum=0.; shortfall=0.
            intake_sum=0.; expense_sum=0.; hv=0.; ha=0.; dv_sum=0.; da_sum=0.; fat_energy=0.
            for day in range(nday):
                beforev=bv; beforea=ba
                dv=bv*pdecay; da=ba*mdecay
                bv = bv-dv+plant[day,cell]; ba=ba-da+meat[day,cell]
                dv_sum+=dv; da_sum+=da
                if prev_delta > 0. and f > .5*fmax: tf=max(hmin,tf-hstep)
                else: tf=min(hmax,tf+hstep)
                bh=body*p
                ev=emax*bv/(bv+crowd*bh) if bv+crowd*bh > 0. else 0.
                ea=emax*ba/(ba+crowd*bh) if ba+crowd*bh > 0. else 0.
                benefits=bv*ev+ba*ea
                if benefits > 0.:
                    hunt=ba*ea/benefits*math.exp(-kdiet*(prev_meat-1.))
                    hunt=min(huntmax,max(huntmin,hunt))
                else: hunt=prev_hunt
                if prev_meat < rmin: hunt=huntmax
                th=tf*hunt; tg=tf-th
                iv=bv/1e6*tg*ev*search
                ia=ba/1e6*th*ea*search
                if p > 0.:
                    iv=min(iv,bv/p); ia=min(ia,ba/p)
                else:
                    iv=0.; ia=0.
                expense=basal+activity*tf
                potential=food*(iv+ia)
                # Published intake/fat ceiling: surplus food is not extracted.
                allowed=max(0.,expense+(fmax-f)*mplus)
                if potential > allowed and potential > 0.:
                    factor=allowed/potential;iv*=factor;ia*=factor
                intake=food*(iv+ia)
                balance=intake-expense
                conversion=mplus if balance >= 0. else mminus
                delta=balance/conversion
                f += delta
                fat_energy += conversion*delta
                if f > fmax: f=fmax  # roundoff only after the intake ceiling
                residual=abs(balance-conversion*delta)
                maxenergy=max(maxenergy,residual)
                maxenergyrel=max(maxenergyrel,residual/max(1.,abs(intake)+expense))
                harvestv=iv*p; harvesta=ia*p
                bv=max(0.,bv-harvestv); ba=max(0.,ba-harvesta)
                rv=abs(beforev+plant[day,cell]-dv-harvestv-bv)
                ra=abs(beforea+meat[day,cell]-da-harvesta-ba)
                maxmass=max(maxmass,rv,ra)
                maxmassrel=max(maxmassrel,rv/max(1.,beforev+plant[day,cell]+dv+harvestv+bv),
                    ra/max(1.,beforea+meat[day,cell]+da+harvesta+ba))
                hv+=harvestv;ha+=harvesta
                x=max(-700.,min(700.,bslope*(f/fmax-.5)))
                birth += bmax/(1.+math.exp(-x))
                starve += .5*math.erfc(f/(fsigma*fmax*math.sqrt(2.)))
                hours+=tf;iv_sum+=iv;ia_sum+=ia
                intake_sum+=intake;expense_sum+=expense
                if intake < expense: shortfall+=1.
                prev_delta=delta
                prev_meat=ia/(iv+ia) if iv+ia > 0. else 0.
                prev_hunt=hunt
            birth/=nday;starve/=nday
            growth=birth-starve-mb
            p=max(pfloor,p*(1.+growth))
            # Catabolic annual reproductive energy is an explicit convention.
            repro_energy=repro*birth
            f -= repro_energy/mminus
            pdiff=abs(p-oldp)/max(pfloor,oldp,1e-12)
            fdiff=abs(f-oldf)/max(1.,fmax)
            vdiff=abs(bv-oldbv)/max(1.,abs(oldbv))
            adiff=abs(ba-oldba)/max(1.,abs(oldba))
            if year+1 >= max(min_years,averaging_years) and max(pdiff,fdiff,vdiff,adiff) <= tolerance:
                stable+=1
            else: stable=0
            if stable >= stable_years:
                converged=True
            floor_limited = p <= pfloor*(1.+1e-10) and growth <= 0.
            out[0,cell]=p;out[1,cell]=hours/nday
            out[2,cell]=ia_sum/(iv_sum+ia_sum) if iv_sum+ia_sum > 0. else 0.
            out[3,cell]=shortfall;out[4,cell]=f
            out[5,cell]=birth;out[6,cell]=starve;out[7,cell]=growth
            out[8,cell]=bv;out[9,cell]=ba
            out[10,cell]=intake_sum;out[11,cell]=expense_sum;out[12,cell]=repro_energy
            out[13,cell]=hv;out[14,cell]=ha;out[15,cell]=dv_sum;out[16,cell]=da_sum
            out[17,cell]=unused;out[18,cell]=maxmass;out[19,cell]=maxenergy
            out[20,cell]=year+1;out[21,cell]=1. if converged else 0.
            out[22,cell]=1. if floor_limited else 0.
            out[23,cell]=maxmassrel;out[24,cell]=maxenergyrel
            out[25,cell]=annual_plant_input;out[26,cell]=annual_meat_input
            out[41,cell]=oldbv;out[42,cell]=oldba;out[43,cell]=oldf
            out[44,cell]=fat_energy-repro_energy
            slot=year % averaging_years
            history[slot,0]=p
            history[slot,1]=hours/nday
            history[slot,2]=ia_sum
            history[slot,3]=iv_sum
            history[slot,4]=shortfall
            history[slot,5]=birth
            history[slot,6]=starve
            history[slot,7]=growth
            history[slot,8]=f
            history[slot,9]=1. if floor_limited else 0.
            if converged: break
        window=min(year+1,averaging_years)
        means=np.zeros(10)
        lowest=history[0,0];highest=lowest;supported=0.
        for j in range(window):
            for k in range(10):means[k]+=history[j,k]/window
            lowest=min(lowest,history[j,0]);highest=max(highest,history[j,0])
            if history[j,9]<.5:supported+=history[j,0]/window
        variance=0.
        for j in range(window):variance+=(history[j,0]-means[0])**2/window
        out[27,cell]=means[0];out[28,cell]=math.sqrt(variance)
        out[29,cell]=lowest;out[30,cell]=highest
        out[31,cell]=means[1]
        out[32,cell]=means[2]/(means[2]+means[3]) if means[2]+means[3]>0. else 0.
        out[33,cell]=means[4];out[34,cell]=means[5];out[35,cell]=means[6]
        out[36,cell]=means[7];out[37,cell]=means[8];out[38,cell]=means[9]
        out[39,cell]=window;out[40,cell]=supported
    return out


def simulate_foraging(plant_supply, meat_supply, *, params=ForagingParams(),
        initial_density=.1, initial_fat_kg=7.5, years=300, min_years=20,
        convergence_rtol=.01, convergence_years=5, averaging_years=50, day_weights=None):
    """Simulate repeating daily food inputs and annual population feedback.

    ``plant_supply`` and ``meat_supply`` have shape ``[day, ...cells]`` and
    units kg dry matter / km² / day. The day axis is a complete repeated year.
    A supply is a new external edible-food input, not a stock or total NPP.
    Stocks begin empty. With annual meat reset enabled, provide a prey budget
    on the first day and zeros thereafter for an annual stock/depletion model.

    The four display outputs are averages over the final ``averaging_years``
    (50 in the source paper), rather than arbitrary terminal population phases.
    Terminal values and population ranges remain separately available.
    Final density is a realized model scenario, never an independently measured
    maximum support. ``converged`` certifies repeated annual state only under
    the declared tolerance and initial state; false must remain visible. The
    numerical population floor is returned separately; unsupported floor-limited
    cells report zero in the display density, while raw density is retained.
    ``scarcity_days_year`` counts intake below expenditure, including ordinary
    reserve drawdown; it is not a census of famine days or starvation deaths.
    """
    params.validate()
    plant=np.asarray(plant_supply,float);meat=np.asarray(meat_supply,float)
    if (plant.ndim < 1 or plant.shape != meat.shape or not 1 <= plant.shape[0] <= 2000
            or not np.isfinite(plant).all() or not np.isfinite(meat).all()
            or (plant < 0).any() or (meat < 0).any()):
        raise ValueError('Need matching finite nonnegative daily edible-resource supplies')
    if day_weights is not None:
        weights=np.asarray(day_weights,float)
        if weights.shape != (plant.shape[0],) or not np.array_equal(weights,np.ones_like(weights)):
            raise ValueError('The daily FORGE kernel requires individual equal-duration days')
    if (not isinstance(years,int) or isinstance(years,bool) or years < 1
            or not isinstance(min_years,int) or min_years < 1 or min_years > years
            or not isinstance(convergence_years,int) or convergence_years < 1
            or not isinstance(averaging_years,int) or isinstance(averaging_years,bool) or averaging_years < 1
            or not math.isfinite(convergence_rtol) or not 0 < convergence_rtol < 1):
        raise ValueError('Need positive finite annual convergence settings')
    spatial=plant.shape[1:]
    p=np.broadcast_to(np.asarray(initial_density,float),spatial).reshape(-1).copy()
    f=np.broadcast_to(np.asarray(initial_fat_kg,float),spatial).reshape(-1).copy()
    if (not np.isfinite(p).all() or not np.isfinite(f).all() or (p < 0).any()
            or (f < 0).any() or (f > params.max_fat_kg).any()):
        raise ValueError('Need nonnegative initial density and physical fat within its ceiling')
    p=np.maximum(p,params.population_floor_people_km2)
    values=asdict(params)
    packed=np.array([float(values[name]) for name in values],float)
    flat=_simulate_flat(np.ascontiguousarray(plant.reshape(plant.shape[0],-1)),
        np.ascontiguousarray(meat.reshape(meat.shape[0],-1)),packed,p,f,
        years,min_years,convergence_rtol,convergence_years,averaging_years)
    result={name:flat[i].reshape(spatial) for i,name in enumerate(_OUTPUT_NAMES)}
    for name in ('converged','floor_limited'):
        result[name]=result[name].astype(bool)
    result['years_simulated']=result['years_simulated'].astype(np.int32)
    result['unsupported']=(result['floor_year_fraction'] >= 1.-1e-12) | ((result['annual_plant_supply_kg_dm_km2']+result['annual_meat_supply_kg_dm_km2']) <= 0.)
    result['terminal_density_people_km2']=result['raw_density_people_km2'].copy()
    result['density_people_km2']=np.where(result['unsupported'],0.,result['mean_supported_density_people_km2'])
    for name in ('foraging_hours_day','meat_fraction','scarcity_days_year'):
        result['terminal_'+name]=result[name].copy()
        result[name]=result['mean_'+name].copy()
    result['averaging_years_used']=result['averaging_years_used'].astype(np.int32)
    result['density_cv']=np.divide(result['density_std_people_km2'],result['mean_density_people_km2'],
        out=np.zeros(spatial),where=result['mean_density_people_km2']>0)
    result['fat_kg'],result['energy_debt_mj']=fat_components(result['effective_fat_kg'],params)
    result['days_per_year']=plant.shape[0]
    result['requested_averaging_years']=averaging_years
    result['display_statistic']='Final-window arithmetic annual means (diet share weighted by consumed food); strict annual-state convergence is separate.'
    result['parameters']=values
    result['source']=SOURCE.copy()
    result['ledger_scope']='Daily resource conservation and asymmetric fat-energy conversion; annual reproduction separately debited. Population itself changes annually, so per-capita annual ledgers are not whole-population energy accounts.'
    return result
