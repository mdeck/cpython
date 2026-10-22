"""Prepare exact Python variants from a CPython checkout containing both commits.

Run with the newly built CPython to launch timings; use --prepare-only to stop
before benchmarking. The evidence branch includes the candidate as an ancestor.
"""
from pathlib import Path
import subprocess, sys
root=Path(__file__).resolve().parent
repo=next(p for p in root.parents if (p/'Include'/'Python.h').is_file())
(root/'variants').mkdir(exist_ok=True)
for name,sha in [('main','97d361116f27d9a53ff735151ba26f5bcb463b74'),('candidate','6c72434f0e04c950a3908ebf40b1b5d27f64c72a')]:
    data=subprocess.check_output(['git','show',sha+':Lib/inspect.py'],cwd=repo)
    (root/'variants'/(name+'.py')).write_bytes(data)
subprocess.run([sys.executable,str(root/'prepare_variants.py')],cwd=root,check=True)
if '--prepare-only' not in sys.argv:
    for name in ['differential.py','check_zipimport.py','benchmark.py','benchmark_cold_stack.py','warm_crossover.py']:
        subprocess.run([sys.executable,str(root/name)],cwd=root,check=True)
