cd /home/user/rotclimate; S=/tmp/claude-0/-home-user-rotclimate/102a023a-f7ac-5ee0-b069-1ee48d6f8e91/scratchpad
for v in '{}' '{"cold_high_storms": 0.0}' '{"cold_high_storms": 0.3}' '{"edge_continental_drying": 0.0}' '{"far_fetch": 0.0}' '{"storm_seasonality": 0.4}'; do
  n=w_$(echo "$v" | md5sum | cut -c1-6)
  [ -f $S/$n/summary.json ] || .venv/bin/python scripts/benchmark_local.py --fit calibration/local_accuracy_20261023/r44_params.json --set "$v" --regions kazakh_steppe middle_volga mongolia canadian_prairies north_china_plain eastern_europe manchuria us_midwest --region-specs $S/winter_specs.json --workers 4 --out $S/$n > $S/$n.log 2>&1
  python3 - "$S/$n" "$v" <<'P'
import json,sys,numpy as np
d=json.load(open(sys.argv[1]+'/summary.json'))['regions']; out=[]
for k in ('kazakh_steppe','middle_volga','mongolia','canadian_prairies','north_china_plain','eastern_europe','manchuria','us_midwest'):
    c=np.load(f'{sys.argv[1]}/cells/{k}.npz'); cold=np.argsort(c['To'],0)[:3]
    out.append('%s %.3f w%.0f/%.0f'%(k[:6],d[k]['rain']['loss'],np.median(np.take_along_axis(c['Ps'],cold,0).sum(0)),np.median(np.take_along_axis(c['Po'],cold,0).sum(0))))
print(sys.argv[2],'| mean loss %.4f |'%np.mean([d[k]['rain']['loss'] for k in d]),' '.join(out))
P
done
