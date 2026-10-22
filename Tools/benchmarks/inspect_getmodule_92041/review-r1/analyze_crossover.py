from pathlib import Path
import json, math
import numpy as np
root=Path(__file__).resolve().parent
rows=json.loads((root/'warm-crossover-raw.json').read_text());rng=np.random.default_rng(20261023);output=[]
for base,test in sorted({(r['base'],r['test']) for r in rows}):
 for work in sorted({r['workload'] for r in rows}):
    rs=[r for r in rows if r['base']==base and r['test']==test and r['workload']==work]
    logs=np.array([np.mean([math.log(r['base_us']/r['test_us']) for r in rs if r['process']==i]) for i in sorted({r['process'] for r in rs})])
    bootstrap=np.exp(np.mean(logs[rng.integers(0,len(logs),(20000,len(logs)))],axis=1));lo,hi=np.quantile(bootstrap,[.025,.975])
    row={'base':base,'test':test,'workload':work,'processes':len(logs),'paired_batches':len(rs),'geomean_speedup':math.exp(float(np.mean(logs))),'speedup_95ci':[float(lo),float(hi)],'base_median_us':float(np.median([r['base_us'] for r in rs])),'test_median_us':float(np.median([r['test_us'] for r in rs]))}
    output.append(row);print(row)
(root/'warm-crossover-summary.json').write_text(json.dumps(output,indent=2))
