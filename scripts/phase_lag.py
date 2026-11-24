import numpy as np,glob,json,sys,collections
d=sys.argv[1]; who=sys.argv[2] if len(sys.argv)>2 else 'candidate'
rm=json.load(open('calibration/regimes_20261124/regimes_v2.json'))['regimes']
e=np.exp(-2j*np.pi*np.arange(12)/12)
rows=[];agg=collections.defaultdict(list)
for f in sorted(glob.glob(d+who+'_*/cells/*.npz')):
  n=f.split('/')[-1][:-4]
  if n not in rm: continue
  z=np.load(f);s=(z['Ts']*e[:,None]).sum(0);o=(z['To']*e[:,None]).sum(0)
  lag=np.angle(s/o)*-365/(2*np.pi)  # days sim lags obs (+)
  amp=np.abs(s)/np.abs(o)
  w=np.abs(o)
  L=(lag*w).sum()/w.sum();A=(amp*w).sum()/w.sum()
  if np.abs(o).mean()/6<2: L=np.nan  # weak seasonal cycle
  rows.append((L,A,n,rm[n],z['lat'].mean()));agg[rm[n]].append((L,A))
rows.sort(key=lambda r:-np.nan_to_num(r[0]))
for r in rows: print("lag%+5.1fd amp%5.2f %-20s %-13s lat%+.0f"%r)
for k,v in agg.items():
  a=np.array(v);print(k,'lag',np.round(np.nanmean(a[:,0]),1),'amp',np.round(a[:,1].mean(),2))
