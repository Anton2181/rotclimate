"""Explicit committed source transitions for a new opt-in ocean experiment.

Historical protocols are immutable. Only four named core files may advance;
both versions must match declared Git bytes and the running version must be
the new one. Raw inputs and every other source must still match exactly.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash, identity

CORE = {'rotclimate/config.py', 'rotclimate/model.py', 'rotclimate/joint.py', 'rotclimate/column_thermodynamics.py'}


def validate_epoch(epoch):
    if set(epoch['files']) != CORE:
        raise ValueError('Ocean epoch must explicitly bind exactly four core files')
    for name, hashes in epoch['files'].items():
        for which in ['before', 'after']:
            payload = subprocess.check_output(['git', 'show', epoch[which + '_commit'] + ':' + name], cwd=ROOT)
            if hashlib.sha256(payload).hexdigest() != hashes[which + '_sha256']:
                raise ValueError('Declared Git source bytes differ: ' + name)
        if hashes['before_sha256'] == hashes['after_sha256'] or file_hash(ROOT / name) != hashes['after_sha256']:
            raise ValueError('Running ocean core is not the declared new version: ' + name)


def current_sources(historical, epoch):
    result = {}
    for name, sha in historical.items():
        if name in epoch['files']:
            if sha != epoch['files'][name]['before_sha256']:
                raise ValueError('Unexpected historical core version: ' + name)
            result[name] = epoch['files'][name]['after_sha256']
        else:
            result[name] = sha
        if file_hash(ROOT / name) != result[name]:
            raise ValueError('Undeclared changed source/input: ' + name)
    return result


def reference_sources(plan):
    """Bind both old reference records and refresh unchanged thermal arithmetic."""
    from rotclimate.column_thermodynamics import integrate_saturation_profile, specific_saturation
    sources, certificates = {}, {}
    for kind, entry in plan['ocean_profile_pilot']['references'].items():
        folder = ROOT / entry['directory']
        protocol = json.loads((folder / 'protocol.json').read_text())
        review = json.loads((folder / 'review.json').read_text())
        if (review['identity'] != identity(protocol) or not review['complete'] or review['status'] != 'passed'
                or review['climate_integrations'] != 0 or review['physics_or_atlas_adoption'] is not False):
            raise ValueError('Invalid historical reference: ' + kind)
        for filename, key in [('protocol.json', 'protocol_sha256'), ('review.json', 'review_sha256'), ('native_profiles.npz', 'arrays_sha256')]:
            actual = file_hash(folder / filename)
            if actual != entry[key] or (filename != 'review.json' and actual != review[key]):
                raise ValueError('Changed reference record/arrays: ' + kind)
            sources[str((folder / filename).relative_to(ROOT))] = actual
        sources.update(current_sources(protocol['sources'], plan['source_epoch']))
        if kind == 'thermal':
            if review['reviews']['environmental_6']['qualifies'] is not True:
                raise ValueError('Environmental thermal reference did not qualify')
            maximum = 0.
            with np.load(folder / 'native_profiles.npz', allow_pickle=False) as z:
                for region in ['pacific_nw', 'iberia', 'california']:
                    anchor = z[region + '_observed_temperature_c'][:, 0]
                    pressure = z[region + '_pressure_hpa']
                    ps = np.full_like(anchor, 92500.)
                    edges = np.broadcast_to(pressure[:, None, None] * 100., (7,) + ps.shape)
                    _, interfaces = integrate_saturation_profile(anchor, ps, edges, profile='lapse', lapse_k_km=6., steps=64)
                    actual = specific_saturation(np.moveaxis(interfaces, 0, 1), pressure[None, :, None] * 100.)
                    old = z[region + '_environmental_6_specific_saturation_kg_kg']
                    np.testing.assert_allclose(actual, old, rtol=1e-12, atol=1e-14)
                    maximum = max(maximum, float(np.max(np.abs(actual - old))))
            certificates[kind] = dict(archived_qualification_retained=True, refreshed_native_saturation_max_abs_error=maximum)
        elif kind == 'marine_rh':
            if review['reviews']['half_taper']['supports_separately_declared_coupled_pilot'] is not True:
                raise ValueError('Marine RH process comparison lacks half-taper support')
            certificates[kind] = dict(archived_reference_support_retained=True,
                                      scope='Reference outcome retained; this is not a claimed coupled response')
        else:
            raise ValueError('Unknown ocean reference type')
    return sources, certificates
