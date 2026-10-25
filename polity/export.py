"""Political reach layers for an atlas: control over the year and in the
hardest month, what limits it, days beyond the network, days from the
imperial capital, the sailing season, refuge terrain and who reaches where.

    python3 -I scripts/export_reach.py atlases/free_fit
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from . import control as C
from .fields import CONTESTED_DAYS, HELD_DAYS, LAYERS, MOUNTED, compute
from .seasons import MONTHS

ROOT = Path(__file__).resolve().parents[1]
CONTROL_RAMP = ['#4d1a17', '#8f3426', '#c8603a', '#e5a557', '#e8d98a', '#9fbf5f', '#4f8f4a', '#1f5f3a']
DAYS_RAMP = CONTROL_RAMP[::-1]
SEA_RAMP = ['#dfe8f1', '#b9cfe5', '#8fb3d8', '#6597c9', '#3f78b4', '#255b96', '#143f73']
# tiered colours: control by the days out it means (exp(-days)), days in walking terms
CONTROL_TIERS = ([0, 2, 5, 13, 22, 37, 50, 61, 78, 100],
                 ['< 2 % · 4+ days out', '2–5 % · 3–4 days', '5–13 % · 2–3 days', '13–22 % · 1½–2 days',
                  '22–37 % · 1–1½ days', '37–50 % · 17–24 h', '50–61 % · 12–17 h', '61–78 % · 6–12 h', '≥ 78 % · under 6 h'])
DAYS_TIERS = ([0, .25, .5, 1, 1.5, 2, 3, 4, 6],
              ['under 6 h', '6–12 h', '½–1 day', '1–1½ days', '1½–2 days', '2–3 days', '3–4 days', '4+ days'])
CAPITAL_TIERS = ([0, 5, 10, 15, 20, 30, 45, 60],
                 ['under 5 days', '5–10 days', '10–15 days', '15–20 days', '20–30 days', '30–45 days', '45+ days'])
MONTH_TIERS = ([0, 1, 3, 6, 9, 11, 12, 12.01],
               ['none', '1–2 months', '3–5', '6–8', '9–10', '11', 'all year'])
SEA_TIERS = ([0, 1, 2, 3, 4, 5, 6, 8],
             ['never safe', '1 month', '2 months', '3 months', '4 months', '5 months', '6 or more'])
REFUGE_TIERS = ([0, 50, 70, 80, 90, 95, 100.01],
                ['under half kept', '50–70 %', '70–80 %', '80–90 %', '90–95 %', '95–100 %'])
CAUSES = [('#cfcabd', 'nothing much: open going'), ('#8fb8de', 'lasting snow'), ('#8a6a3f', 'mud'),
          ('#e08a3c', 'heat'), ('#3f6fb5', 'rivers in flood')]


def travel_note():
    from . import transport as X
    from . import seasons as S
    return ('Days for an official or a patrol, month by month. On foot: roads 30 km a day, Tobler\'s hiking speed off '
            'them for 7 hours a day, slowed by Soule & Goldman terrain coefficients (forest 1.5, swamp 1.8, desert 1.6, '
            f'lasting snow 2.5, mud up to {S.MUD_COEFFICIENT:g}, and the midday heat), quickened by footpaths where '
            'people farm; fords take longer in floods. By ship: '
            f'{X.SAIL_FAIR_KNOTS:g} knots before a fair wind (Casson 1951), less along coasts and much less against '
            'the wind, by the month\'s winds from the climate model, halved when the sea is uncertain and nearly shut '
            'in the storm months (thresholds fitted to Vegetius); boarding at ports, landing on any shore. By river '
            f'boat: {X.RIVER_DOWN_KM_DAY:.0f} km a day downstream, {X.RIVER_UP_KM_DAY:.0f} up (ORBIS), the upper '
            'rivers shut at low water. Unmarked towns (spaced as Chinese county seats were) and their minor roads are added as on '
            'the "Unmarked towns and tracks" layer. Herding polities ride (50 km a day over open country). Year-round '
            'values average the control of the twelve months. Fitted and tested on Han China and the Roman empire '
            '(calibration/polity_20261025).')


def export(atlas, trade_scheme='directed'):
    if trade_scheme not in ('legacy','directed'):
        raise ValueError('Unknown trade scheme')
    from harvest.export import color_image, tiers
    from rotclimate.geography import source_layers
    atlas = Path(atlas); data = atlas / 'data'
    meta = json.loads((data / 'atlas.json').read_text())
    r = compute(atlas)
    land, elev, f = r['land'], r['elev'], r['fields']
    coast = source_layers()['land']
    note = travel_note()

    def save(rgb, filename, sea=True):
        image = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
        image = image.resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
        pixels = np.array(image)
        if sea:
            pixels[~coast] = [214, 227, 240]
        Image.fromarray(pixels).save(data / filename, 'WEBP', quality=88, method=4)

    def shade(rgb):
        gy, gx = np.gradient(elev)
        return np.clip(rgb * np.clip(.96 - .00018 * gx + .00022 * gy, .78, 1.08)[..., None], 0, 1)

    layers = []

    def ramp(lid, value, label, unit, lo, hi, stops, note_, tier, mask=None, sea=True):
        img = color_image(value, land if mask is None else mask, elev, stops, lo, hi)
        save(img, lid + '.webp', sea)
        t = tiers(stops, lo, hi, False, *tier)
        t['file'] = lid + '_tiers.webp'
        save(color_image(value, land if mask is None else mask, elev, stops, lo, hi, tiered=t), t['file'], sea)
        layers.append(dict(id=lid, file=lid + '.webp', label=label, kind='ramp', group='Political reach',
                           unit=unit, vmin=lo, vmax=hi, stops=stops, note=note_, log=False, tiers=t))
    ramp('reach_control', 100 * r['control_open'], 'Effective control', '% · exp(−days / 1 day) from the nearest '
         'road, town, fort or monastery, marked or unmarked, averaged over the twelve months', 0, 100, CONTROL_RAMP,
         'One day out and one day back is the reach a county seat or a fort holds directly; at two days a third of it '
         'remains. ' + rank_note() + note, CONTROL_TIERS)
    ramp('reach_control_winter', 100 * r['control_winter'], 'Control in the hardest month', '% · as above, in each '
         'place\'s own worst month (snow, mud, floods, heat or storms at sea)', 0, 100, CONTROL_RAMP, note,
         CONTROL_TIERS)
    ramp('reach_months', f['months_within_day'].astype(float), 'Months within a day', 'months a year within a day '
         'of the network (control ≥ 37 %)', 0, 12, CONTROL_RAMP, note, MONTH_TIERS)
    ramp('reach_days', np.minimum(f['days_open'], 6), 'Days beyond the roads', 'days on foot or by boat to the nearest '
         'road, town, fort or monastery, marked or unmarked (year-round: the days of the average control)', 0, 6,
         DAYS_RAMP, note, DAYS_TIERS)
    ramp('reach_capital', np.minimum(f['capital_days_open'], 60), 'Days from the capital', 'days from the imperial '
         'capital by road, track, sea and river, the mean of the twelve months', 0, 60, DAYS_RAMP, note, CAPITAL_TIERS)
    if C.REFUGE_PER_KM != 0:
        ramp('reach_refuge', 100 * r['refuge'], 'Refuge terrain', f'% of control kept: exp({C.REFUGE_PER_KM:+.2f} × '
             'relief in km), the relief over ~26 km', 0, 100, CONTROL_RAMP,
             'Hills and gorges shelter people from the state beyond what the walking time says: in Han China the '
             'registered people per modelled person fell with the relief of the commandery (Scott 2009, The Art of '
             'Not Being Governed). Fitted on the census of AD 2, tested on the Roman towns.', REFUGE_TIERS)
    # the sailing season
    water = r['water']
    gy, gx = np.gradient(elev)
    sea_val = np.minimum(f['sea_open_months'].astype(float), 8)
    t = tiers(SEA_RAMP, 0, 8, False, *SEA_TIERS)
    for tiered, fname in ((None, 'reach_sea.webp'), (t, 'reach_sea_tiers.webp')):
        rgb = color_image(sea_val, water, np.zeros_like(elev), SEA_RAMP, 0, 8, tiered=tiered)
        grey = np.clip(0.66 + 0.12 * (.96 - .00018 * gx + .00022 * gy), 0.55, 0.82)[..., None] * np.array([1, .98, .94])
        rgb = np.where(water[..., None], rgb, grey)
        save(rgb, fname, sea=False)
    t['file'] = 'reach_sea_tiers.webp'
    layers.append(dict(id='reach_sea', file='reach_sea.webp', label='Safe sailing season', kind='ramp',
                       group='Political reach', unit='months a year the sea is safe (Vegetius\' certain season); '
                                                    'ships still sail, at half speed, in the uncertain months',
                       vmin=0, vmax=8, stops=SEA_RAMP, log=False, tiers=t,
                       note='Storminess from the swing of the wind about its mean (the open oceans of Earth by latitude '
                            'and month, NCEP/NCAR), against the thresholds that best reproduce Vegetius\' sailing '
                            'season in the Mediterranean (safe late May to mid September, closed mid November to mid '
                            'March); strong mean winds (Beaufort 5 and 6) also shut it, as the monsoon shut the west '
                            'Indian ports. ' + note))
    # what limits travel in the hardest month
    cause = f['hardest_cause']
    rgb = np.ones(land.shape + (3,)) * np.array([.93, .91, .86])
    for k, (col, _) in enumerate(CAUSES):
        m = land & (cause == k)
        rgb[m] = np.array([int(col[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    rgb = shade(rgb); rgb[~land] = [.84, .89, .94]
    save(rgb, 'reach_cause.webp')
    counts = np.bincount(cause[land].ravel(), minlength=len(CAUSES))
    month_counts = np.bincount(f['hardest_month'][land].ravel(), minlength=12)
    layers.append(dict(id='reach_cause', file='reach_cause.webp', label='What closes the roads', kind='categories',
                       group='Political reach',
                       items=[dict(color=c, label=f'{lab} · {100 * n / max(land.sum(), 1):.0f} % of the land')
                              for (c, lab), n in zip(CAUSES, counts)],
                       note='The strongest of snow, mud, heat and floods in each place\'s hardest month (the month of its '
                            'lowest control). The hardest months over the land: ' +
                            ', '.join(f'{MONTHS[m]} {100 * n / max(land.sum(), 1):.0f} %' for m, n in
                                      sorted(enumerate(month_counts), key=lambda x: -x[1])[:4]) +
                            ' (months from the winter solstice). ' + note))

    # who reaches where
    best, best_days = f['polity_best'], f['polity_best_days']
    strength = np.clip(np.exp(-np.nan_to_num(best_days, nan=99, posinf=99)), 0, 1)
    rgb = np.ones(land.shape + (3,)) * np.array([.93, .91, .86])
    for k, name in enumerate(r['polity_names']):
        m = land & (best == k)
        col = np.array(r['polity_rgb'][name]) / 255.0
        rgb[m] = col * strength[m, None] + np.array([.93, .91, .86]) * (1 - strength[m, None])
    yy, xx = np.mgrid[:land.shape[0], :land.shape[1]]
    hatch = r['contested'] & ((xx + yy) % 5 == 0)
    rgb[hatch] = rgb[hatch] * .45
    rgb = shade(rgb)
    rgb[~land] = [.84, .89, .94]
    save(rgb, 'reach_polities.webp')
    area = r['cell_km'] ** 2
    items = []
    for k, name in enumerate(r['polity_names']):
        held = float((r['held'] & (best == k)).sum() * area)
        if held > 0:
            ride = ' · rides (herders)' if r['mobile'][name] else ''
            items.append(dict(color='#%02x%02x%02x' % tuple(r['polity_rgb'][name]),
                              label=f'{name} · {held / 1000:,.0f} k km² held{ride}'))
    layers.append(dict(id='reach_polities', file='reach_polities.webp', label='Who reaches where', kind='categories',
                       group='Political reach', items=items,
                       note=f'Each place takes the polity whose own roads and towns, marked or unmarked, are nearest in days '
                            f'over the year; the colour fades with the days (exp(−days)). Hatched: contested, a rival '
                            f'within {CONTESTED_DAYS:g} day. Held = within {HELD_DAYS:g} days (tested on the Roman '
                            f'empire of AD 150). ' + (f'Riding polities ({", ".join(sorted(MOUNTED))}) reach from '
                            f'wherever their herds graze. ' if MOUNTED else 'No polity is set to ride: on Earth the '
                            f'land\'s herding share did not pick out the steppe peoples, so riding is set by lore. ')
                            + note))
    from . import defacto as DF
    from . import trade as TR
    dfs = DF.map_fields(r)
    layers.append(defacto_layer(r, dfs, meta, data, elev, coast, note))
    if trade_scheme=='directed':
        from .directed_trade import map_fields
        tr=map_fields(r,progress=lambda message:print(message,flush=True))
    else:
        tr = TR.map_fields(r)
    layers.append(trade_layer(r, tr, meta, data, elev, coast))
    from . import mapdata
    mapdata.write(r, dfs, tr, data / 'vectors', DF.FILL_DAYS)
    cache(atlas, r, dfs, tr)
    # the suggested unmarked towns and minor roads
    from PIL import ImageDraw
    base = color_image(np.zeros(land.shape), land, elev, ['#efe9d8', '#efe9d8'], 0, 1)
    image = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).resize((meta['width'], meta['height']),
                                                                                  Image.Resampling.NEAREST)
    px = np.array(image); px[~coast] = [214, 227, 240]; image = Image.fromarray(px)
    draw = ImageDraw.Draw(image)
    sx, sy = meta['width'] / land.shape[1], meta['height'] / land.shape[0]
    ry, rx = np.nonzero(r['river'])
    for q, c in zip(ry, rx):
        draw.rectangle([c * sx, q * sy, (c + 1) * sx - 1, (q + 1) * sy - 1], fill=(92, 140, 196))
    for path in r['routes']:
        if len(path) > 1:
            draw.line([((c + .5) * sx, (q + .5) * sy) for q, c in path], fill=(139, 90, 43), width=1)
    ry, rx = np.nonzero(r['road'])
    for q, c in zip(ry, rx):
        draw.rectangle([c * sx, q * sy, (c + 1) * sx - 1, (q + 1) * sy - 1], fill=(232, 106, 20))
    for q, c in r['suggested']:
        x, y = (c + .5) * sx, (q + .5) * sy
        draw.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(170, 170, 170), outline=(40, 40, 40))
    for q, c in r['ports']:
        x, y = (c + .5) * sx, (q + .5) * sy
        draw.rectangle([x - 2, y - 2, x + 2, y + 2], outline=(20, 60, 120), width=1)
    image.save(data / 'reach_towns.webp', 'WEBP', quality=90, method=4)
    layers.append(dict(id='reach_towns', file='reach_towns.webp', label='Unmarked towns and tracks', kind='categories',
                       group='Political reach',
                       items=[dict(color='#aaaaaa', label=f"{len(r['suggested']):,} suggested unmarked towns"),
                              dict(color='#8b5a2b', label=f"minor roads · {r['tracks'].sum() * r['cell_km']:,.0f} km"),
                              dict(color='#e86a14', label='the marked roads'),
                              dict(color='#5c8cc4', label='navigable rivers (river boats)'),
                              dict(color='#143c78', label=f"{len(r['ports']):,} ports (boxed)")],
                       note='Where a populated countryside would have market towns and county seats that the map does not '
                            'mark, spaced as Chinese county seats were (seats go with people^0.7 × area^0.3: one per 40,000 people '
                            'at Han densities, fewer and larger towns where people are dense, more where thin; fitted on '
                            'Han AD 2 and the best rule on Tang, Song and Qing), on the best sites (farming '
                            'people, rivers and lakes, sheltered coasts, flat ground, the marked roads), spaced by the '
                            'density, none in unclaimed land. Minor roads join neighbouring places by their cheapest '
                            'walking routes (a relative neighbourhood graph). Ports: any place within two cells of the '
                            'water. Suggestions, not canon.'))
    meta['layers'] = [l for l in meta['layers'] if not l['id'].startswith('reach_')] + layers
    manifest = json.loads((LAYERS / 'manifest.json').read_text())
    meta['reach'] = dict(defacto=meta.get('reach', {}).get('defacto'),
                         source_sha256=manifest['source_sha256'], held_days=HELD_DAYS, contested_days=CONTESTED_DAYS,
                         model='polity v2 (calibration/polity_20261025)', rank_offset_days=C.RANK_OFFSET_DAYS,
                         refuge_per_km=C.REFUGE_PER_KM,
                         herding={n: {k: round(x, 3) for k, x in v.items()} for n, v in r['herding'].items()},
                         mounted=sorted(MOUNTED))
    meta['reach']['trade']=dict(model=tr.get('model','legacy-outward'),cost_scale=tr['scale'],
                               market_access_direction='outbound')
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False))
    print('Political reach layers written to', data, flush=True)


def write_polities_csv(data, tables):
    """data/polities.csv from the de facto tables: people and km² rounded, shares to 4 places."""
    import csv
    with open(Path(data) / 'polities.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        keys = [k for k in next(iter(tables.values()))['rows'][0] if k != 'polity']
        w.writerow(['gap_fill_days', 'polity'] + keys)
        for c, t in tables.items():
            for row in t['rows']:
                w.writerow([c, row['polity']] + [(round(row[k], 4) if abs(row[k]) < 10 else round(row[k]))
                                                 if isinstance(row[k], float) else row[k] for k in keys])


def fill_label(c):
    return 'none' if c == 0 else ('½ day' if c == 0.5 else f'{c:g} day' + ('s' if c > 1 else ''))


def cache(atlas, r, dfs, tr):
    """The arrays the political plate is drawn from (scripts/render_political_plate.py)."""
    out = ROOT / 'output/polity_map'; out.mkdir(parents=True, exist_ok=True)
    arrays = dict(land=r['land'], elev=r['elev'], claim=r['claim'], second=r['second'], density=r['density'],
                  towns=np.array([[t['row'], t['col']] for t in r['towns']]),
                  kinds=np.array([t['kind'] for t in r['towns']]), ports=np.array(r['ports']),
                  names=np.array(r['polity_names']), rgb=np.array([r['polity_rgb'][n] for n in r['polity_names']]),
                  t_mass=tr['mass'], t_ma=tr['ma'], t_local=tr['ma_local'], e_child=tr['edges'][0],
                  e_parent=tr['edges'][1], e_flow=tr['edges'][2], through=tr['through'], market_owner=tr['catchment'],cell_km=r['cell_km'],
                  river=r['river'], water=r['water'])
    if tr.get('area_ha') is not None:
        arrays['t_area'] = tr['area_ha']
    for c, d in dfs.items():
        tag = f'{int(round(c * 10)):02d}'
        arrays['held_by_' + tag] = d['held_by']; arrays['contested_' + tag] = d['contested']
    np.savez_compressed(out / f'{Path(atlas).name}.npz', **arrays)


def trade_layer(r, tr, meta, data, elev, coast):
    """Trade routes by traffic over a pale relief; towns by the people they serve."""
    from PIL import ImageDraw
    from . import routes as RT
    from . import trade as TR
    from .mapdata import chaikin
    from .render import PAPER, SEA, hillshade
    W, H = meta['width'], meta['height']
    gh, gw = r['land'].shape
    sx, sy = W / gw, H / gh
    land = np.asarray(Image.fromarray(coast.astype(np.uint8) * 255).resize((W, H), Image.BILINEAR)) > 127
    rgb = np.broadcast_to(PAPER, (H, W, 3)) * hillshade(elev, (W, H))[..., None]
    rgb = np.where(land[..., None], rgb, SEA)
    image = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    widths = {'local': 1, 'regional': 2, 'main': 4}
    colours = {'land': (122, 46, 18), 'sea': (25, 70, 125)}
    route_lines = RT.lines(tr, r['water'], r['land'].shape)
    sea_segments=[]
    for cls in ('local', 'regional', 'main'):
        for kind, c, pts, rel in route_lines:
            if c == cls:
                p = chaikin(np.array([((x + .5) * sx, (y + .5) * sy) for y, x in pts]))
                points=[tuple(q) for q in p]
                if kind=='sea':
                    sea_width={'local':2,'regional':3,'main':5}[cls]
                    sea_segments.append((points,sea_width))
                else:
                    draw.line(points,fill=colours[kind],width=widths[cls],joint='curve')
    # Complete the casing pass before any foreground: a later segment's
    # outline must not erase another segment at a junction.
    for points,width in sea_segments:
        draw.line(points,fill=(243,248,252),width=width+3,joint='curve')
    for points,width in sea_segments:
        draw.line(points,fill=colours['sea'],width=width,joint='curve')
    order = np.argsort(tr['mass'])
    big = np.quantile(tr['mass'], [0.5, 0.9, 0.98])
    for i in order:
        t = r['towns'][i]
        x, y = (t['col'] + .5) * sx, (t['row'] + .5) * sy
        rad = 1.5 + 1.2 * int(np.searchsorted(big, tr['mass'][i]))
        draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(251, 248, 240), outline=(30, 30, 30))
    image.save(data / 'reach_trade.webp', 'WEBP', quality=90, method=4)
    sea_cost = TR.SEA_KM_DAY * TR.SEA_PER_KM / TR.ROAD_PER_KM
    shares = ', '.join(f'{100 * s:g} %' for _, s in RT.CLASSES)
    layer=dict(id='reach_trade', file='reach_trade.webp', label='Trade routes', kind='categories',
                group='Political reach',
                items=[dict(color='#7a2e12', label='overland and river routes (width: local, regional, main)'),
                       dict(color='#19467d', label='sea lanes (bundled)'),
                       dict(color='#fbf8f0', label='towns, by the people they serve (four sizes)')],
                note='Goods priced as Diocletian\'s Price Edict priced them: by sea, river and road about 1 : 5 : 28 '
                     'per km (upriver twice downriver); a ship\'s day costs as much as about '
                     f'{sea_cost:.0f} km of road haulage. Each town serves the people nearest it by that cost; trade '
                     'between two towns grows with both their people and falls by a factor of e for every '
                     f'{tr["scale"]:g} road-km of cost (a gravity model), routed along the cheapest paths in each '
                     'season (sea lanes shut in the storm months) and averaged over the year. Classes: segments '
                     f'carrying at least {shares} of the busiest one\'s traffic (land and sea separately); sea '
                     'traffic is bundled into lanes. ' + TRADE_NOTE)
    if tr.get('model')=='inbound-directed':
        layer['note'] += (' Catchments use the countryside’s cost of bringing goods into town. '
                          'Shipments are routed in both directions with their own river and sailing costs; '
                          'relative traffic is not tonnes. Smaller-to-smaller pairs outside the 300 largest '
                          'markets are omitted. Population occupancy and political control are unchanged.')
    return layer


TRADE_NOTE = ('The scale is set, not fitted: hauling wheat 148 km by land cost 55 % of its value (Duncan-Jones 1982), '
              'so road haulage eats a staple\'s whole value at about 270 km. Tested on Earth: market access over this '
              'network did not explain which Roman towns of AD 150 were large (Hanson 2016; Spearman about 0 in the '
              'east), so towns are drawn by the people they serve, not by a predicted size, and the routes are a '
              'model of where trade would run, not a reconstruction. Vector files of every layer: data/vectors/.')


def defacto_layer(r, dfs, meta, data, elev, coast, note):
    """De facto against de jure, one image per gap fill; per-polity people in the legend and in polities.csv."""
    from . import defacto as DF
    from .render import FILL_ALPHA, PAPER, defacto_rgb
    from .fields import rgba
    names = r['polity_names']
    cols = np.array([r['polity_rgb'][n] for n in names]) / 255.0
    borders = rgba('borders.png')
    options, tables = [], {}
    for c in DF.FILL_CHOICES:
        d = dfs[c]
        img = defacto_rgb(d['held_by'], r['claim'], d['contested'], r['second'], cols, elev, coast, borders,
                          (meta['width'], meta['height']))
        fname = f'reach_defacto_fill{int(round(c * 10)):02d}.webp'
        Image.fromarray((img * 255).astype(np.uint8)).save(data / fname, 'WEBP', quality=90, method=4)
        rows, total = DF.polity_table(r, d)
        tables[str(c)] = dict(rows=rows, total=total)
        items = []
        for row in sorted(rows, key=lambda x: -x['held_people']):
            if row['held_km2'] <= 0 and row['claimed_km2'] <= 0:
                continue
            k = names.index(row['polity'])
            shown = PAPER * (1 - FILL_ALPHA) + cols[k] * FILL_ALPHA
            extra = []
            if row['claimed_unheld_people'] >= 5e4:
                extra.append(f"{row['claimed_unheld_people'] / 1e6:.1f} M claimed, unheld")
            if row['claimed_held_by_others_people'] >= 5e4:
                extra.append(f"{row['claimed_held_by_others_people'] / 1e6:.1f} M held by others")
            if row['held_outside_claim_people'] >= 5e4:
                extra.append(f"{row['held_outside_claim_people'] / 1e6:.1f} M beyond its claim")
            items.append(dict(color='#%02x%02x%02x' % tuple(int(round(255 * v)) for v in shown),
                              label=f"{row['polity']} · holds {row['held_people'] / 1e6:.1f} M people on "
                                    f"{row['held_km2'] / 1000:,.0f} k km² · claims {row['claimed_people'] / 1e6:.1f} M"
                                    + (' (' + '; '.join(extra) + ')' if extra else '')))
        held_share = d['bridged'][r['land']].mean()
        options.append(dict(value=f'{c:g}', label=fill_label(c), file=fname, items=items,
                            caption=f"{100 * held_share:.0f} % of the land held · "
                                    f"{total['unclaimed_unheld_people'] / 1e6:.1f} M people neither claimed nor held"))
    meta.setdefault('reach', {})['defacto'] = tables
    write_polities_csv(data, tables)
    default = f'{DF.FILL_DAYS:g}'
    first = next(o for o in options if o['value'] == default)
    return dict(id='reach_defacto', file=first['file'], label='De facto and de jure', kind='categories',
                group='Political reach', items=first['items'],
                variants=dict(label='Gap fill', options=options, default=default),
                note='De jure: the painted borders (lines) and claims. De facto: each place takes the colour of the '
                     f'polity whose own roads and towns are nearest, where that is within {HELD_DAYS:g} days over the '
                     'year. Hatched in a polity\'s colour: land it claims but does not hold (over the holder\'s colour '
                     'where another polity holds it). Hatched the other way: contested, a rival within '
                     f'{CONTESTED_DAYS:g} day. The gap fill bridges unheld gaps narrower than about twice the chosen '
                     'days on foot and leaves larger unheld regions open (a closing in travel time). On Earth, against '
                     'historians\' maps of the Roman empire of AD 150 and Han China of AD 2, fills up to 2 days changed '
                     'the match by under 0.01 (balanced accuracy: west of 20 E 0.831 → 0.830, east 0.811 → 0.819, Han '
                     '0.796 → 0.797), so the default is no fill and the fill is a cartographic choice. People: the '
                     'central occupation scenario; per-polity figures for every fill in data/polities.csv. ' + note)


def rank_note():
    if C.RANK_OFFSET_DAYS > 0:
        return (f'Places are ranked: a county-level place (fortified town, monastery, unmarked town, a road) counts '
                f'as if {C.RANK_OFFSET_DAYS:g} day farther than the seat of a commandery or above (capital, major city, '
                'fortified city, fort), fitted on Han China. ')
    return ('Places were tested for rank on Han China (commandery against county seats) and the data gave no reason to '
            'rank them, so all places count alike. ')


if __name__ == '__main__':
    for path in sys.argv[1:]:
        export(path)
