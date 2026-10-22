import json, math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
rng=np.random.default_rng(20261022)

def analyze(filename):
    rows=json.loads((ROOT/filename).read_text())
    lookup={(r['modules'],r['repeat'],r['variant']):r['measurements_us'] for r in rows}
    pairs=[('main','candidate'),('replacement','combined'),('replacement_fixed','combined_fixed'),('replacement_fixed','replacement_fixed_control')]
    results=[]
    for count in sorted({r['modules'] for r in rows}):
        for base,test in pairs:
            repeats=sorted({r['repeat'] for r in rows if r['modules']==count and r['variant']==base and (count,r['repeat'],test) in lookup})
            if not repeats:continue
            for key in rows[0]['measurements_us']:
                a=np.array([lookup[count,i,base][key] for i in repeats])
                b=np.array([lookup[count,i,test][key] for i in repeats])
                logs=np.log(a/b)
                bootstrap=np.exp(np.mean(logs[rng.integers(0,len(logs),(20000,len(logs)))],axis=1))
                lo,hi=np.quantile(bootstrap,[.025,.975])
                results.append({'modules':count,'base':base,'test':test,'workload':key,'process_pairs':len(repeats),'base_median_us':float(np.median(a)),'test_median_us':float(np.median(b)),'paired_geomean_speedup':math.exp(float(np.mean(logs))),'speedup_95ci':[float(lo),float(hi)],'base_range_us':[float(min(a)),float(max(a))],'test_range_us':[float(min(b)),float(max(b))]})
    return results

all_results=analyze('benchmark-raw.json')+analyze('cold-stack-raw.json')
(ROOT/'statistics.json').write_text(json.dumps(all_results,indent=2))
for row in all_results:
    if row['modules']==10000:
        print('{base:18s} -> {test:26s} {workload:38s} {base_median_us:10.3f} -> {test_median_us:10.3f} us  {paired_geomean_speedup:8.3f}x  [{lo:.3f}, {hi:.3f}]'.format(**row,lo=row['speedup_95ci'][0],hi=row['speedup_95ci'][1]))
