import argparse, gc, importlib.util, json, os, statistics, subprocess, sys, time, timeit, types
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VARIANTS=['main','replacement','candidate','combined','replacement_fixed','combined_fixed','replacement_fixed_control']
REPEATS=15

def worker(variant, count):
    allowed=os.sched_getaffinity(0)
    os.sched_setaffinity(0,{max(allowed)})
    source_variant='replacement_fixed' if variant=='replacement_fixed_control' else variant
    spec=importlib.util.spec_from_file_location('inspect', ROOT/'variants'/(source_variant+'.py'))
    inspect=importlib.util.module_from_spec(spec)
    sys.modules['inspect']=inspect
    spec.loader.exec_module(inspect)
    for i in range(count):
        m=types.ModuleType('_bench_fake_'+str(i));m.__file__=f'/tmp/inspect-bench/{i}.py';sys.modules[m.__name__]=m
    owner=types.ModuleType('_bench_owner'); owner.__file__=str(ROOT/'bench_workload.py');sys.modules[owner.__name__]=owner
    owner.inspect=inspect
    exec(compile((ROOT/'bench_workload.py').read_text(),owner.__file__,'exec'),owner.__dict__)
    ns={};exec(compile('import sys\nframe=sys._getframe()', '<bench-generated>', 'exec'),ns)
    code=compile('pass','<bench-miss>','exec')
    cached_code=compile('pass',owner.__file__,'exec')
    def cold():
        inspect.modulesbyfile.clear();inspect._filesbymodname.clear()
        return inspect.getmodule(owner.frame)
    marker=types.ModuleType('_bench_mutation'); marker.__file__='/tmp/inspect-churn.py'
    def churn():
        sys.modules[marker.__name__]=marker
        try: return inspect.getmodule(code)
        finally: del sys.modules[marker.__name__]
    def cold_stack(n):
        inspect.modulesbyfile.clear();inspect._filesbymodname.clear()
        return owner.stack(n,0)
    cases={
      'function':lambda:inspect.getmodule(owner.function),
      'registered_frame':lambda:inspect.getmodule(owner.frame),
      'registered_traceback':lambda:inspect.getmodule(owner.tb),
      'cached_code':lambda:inspect.getmodule(cached_code),
      'unregistered_frame':lambda:inspect.getmodule(ns['frame']),
      'bare_code_miss':lambda:inspect.getmodule(code),
      'registry_churn_miss':churn,
      'cold_registered_frame':cold,
      'stack_depth2_context0':lambda:owner.stack(2,0),
      'stack_depth32_context0':lambda:owner.stack(32,0),
      'stack_depth2_context1':lambda:owner.stack(2,1),
      'stack_cold_depth2_context0':lambda:cold_stack(2),
      'stack_cold_depth32_context0':lambda:cold_stack(32),
    }
    class StackTimer:
        def __init__(self, fn): self.fn=fn
        def timeit(self, n):
            start=time.perf_counter()
            for _ in range(n): self.fn()
            return time.perf_counter()-start
    # Warm the pinned core and adaptive specialization before calibration.
    end=time.perf_counter()+.3
    while time.perf_counter()<end:
        inspect.getmodule(owner.frame)
    gc.disable(); result={}
    for name,fn in cases.items():
        # Re-warm after the cold-cache workload as well.
        fn();timer=StackTimer(fn) if name.startswith('stack_') else timeit.Timer(fn);n=1
        while True:
            elapsed=timer.timeit(n)
            if elapsed>=.03:break
            n*=2
        result[name]=statistics.median(timer.timeit(n)/n*1e6 for _ in range(3))
    return result

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='worker':
        print(json.dumps(worker(sys.argv[2],int(sys.argv[3]))));sys.exit()
    records=[]
    for count in (1000,10000):
        for repeat in range(REPEATS):
            # Rotate order to reduce fixed-order thermal/frequency effects.
            order=VARIANTS[repeat%len(VARIANTS):]+VARIANTS[:repeat%len(VARIANTS)]
            for v in order:
                data=json.loads(subprocess.check_output([sys.executable,__file__,'worker',v,str(count)],env={**os.environ,'PYTHONHASHSEED':'0'}))
                records.append(dict(variant=v,modules=count,repeat=repeat,measurements_us=data))
            print(f'{count} modules, repetition {repeat+1}/{REPEATS}',flush=True)
            (ROOT/'benchmark-raw.json').write_text(json.dumps(records,indent=2))
    summary={str(n):{v:{k:statistics.median([r['measurements_us'][k] for r in records if r['variant']==v and r['modules']==n]) for k in records[0]['measurements_us']} for v in VARIANTS} for n in (1000,10000)}
    (ROOT/'benchmark-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
