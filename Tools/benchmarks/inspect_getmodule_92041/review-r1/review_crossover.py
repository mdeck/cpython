import gc, importlib.util, json, os, random, statistics, subprocess, sys, time, types
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PAIRS=[('before','after'),('before','before_control')]

def run(seed):
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
    variants=sorted({v for pair in PAIRS for v in pair});random.Random(seed).shuffle(variants)
    modules={}
    for v in variants:
        source='before' if v=='before_control' else v
        spec=importlib.util.spec_from_file_location('_crossover_'+v,ROOT/'variants'/(source+'.py'))
        m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);modules[v]=m
    for i in range(10000):
        m=types.ModuleType('_cross_fake_'+str(i));m.__file__=f'/tmp/cross/{i}.py';sys.modules[m.__name__]=m
    owner=types.ModuleType('_cross_owner');owner.__file__=str(ROOT/'bench_workload.py');sys.modules[owner.__name__]=owner
    exec(compile(Path(owner.__file__).read_text(),owner.__file__,'exec'),owner.__dict__)
    code=compile('pass',owner.__file__,'exec')
    # Warm every variant's positive cache before the crossed batches.
    for v,m in modules.items():
        owner.inspect=m;m.getmodule(owner.frame)
    def function(v):return modules[v].getmodule(owner.function)
    def registered_frame(v):return modules[v].getmodule(owner.frame)
    def stack(v):
        return owner.stack(2,1)
    incoming=types.ModuleType('_cross_incoming');incoming.__file__='/tmp/cross/incoming.py'
    exec(compile('import sys\nframe=sys._getframe()', incoming.__file__, 'exec'),incoming.__dict__)
    def cold_stack(v):
        m=modules[v];m.modulesbyfile.clear();m._filesbymodname.clear()
        return owner.stack(2,1)
    def incremental(v):
        m=modules[v];m.modulesbyfile.pop(incoming.__file__,None);m._filesbymodname.pop(incoming.__name__,None)
        sys.modules[incoming.__name__]=incoming
        try: assert m.getmodule(incoming.frame) is incoming
        finally: del sys.modules[incoming.__name__]
    cases={'registered_frame':registered_frame,'stack_depth2_context1':stack,'cold_stack':cold_stack,'incremental_frame':incremental}
    def timed(fn,v,n):
        owner.inspect=modules[v]
        start=time.perf_counter()
        for _ in range(n):fn(v)
        return (time.perf_counter()-start)/n*1e6
    gc.disable(); records=[]
    for base,test in PAIRS:
      for key,fn in cases.items():
        n=1
        while timed(fn,base,n)*n<30000:n*=2
        for i in range(4):
            order=[base,test,test,base] if i%2==0 else [test,base,base,test]
            values={base:[],test:[]}
            for v in order:values[v].append(timed(fn,v,n))
            records.append({'process':seed,'base':base,'test':test,'workload':key,'round':i,'base_us':statistics.mean(values[base]),'test_us':statistics.mean(values[test])})
    return records
if __name__=='__main__':
    if len(sys.argv)>1:
        print(json.dumps(run(int(sys.argv[1]))));sys.exit()
    records=[]
    for i in range(8):
        records+=json.loads(subprocess.check_output([sys.executable,__file__,str(i)],env={**os.environ,'PYTHONHASHSEED':'0'}))
        (ROOT/'warm-crossover-raw.json').write_text(json.dumps(records,indent=2));print('crossover process',i+1,'/8',flush=True)
