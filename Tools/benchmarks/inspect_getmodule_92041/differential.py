import importlib.util, itertools, json, os, sys, tempfile, types
from pathlib import Path
ROOT=Path(__file__).resolve().parent
names=['main','candidate','replacement','combined','replacement_fixed','combined_fixed']
mods={}
for name in names:
    spec=importlib.util.spec_from_file_location('inspect_'+name,ROOT/'variants'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);mods[name]=m
results={name:{} for name in names}
with tempfile.TemporaryDirectory() as directory:
    for source_exists,module_suffix,code_suffix,registered,loader,override in itertools.product((False,True),('.py','.pyc','.other'),('.py','.pyc','.other'),(False,True),(False,True),(None,'same','other')):
        source=Path(directory)/'matrix.py';source.write_text('pass\n')
        if not source_exists:source.unlink()
        module=types.ModuleType('_inspect_matrix');module.__file__=str(source.with_suffix(module_suffix))
        if loader:module.__loader__=object()
        sys.modules[module.__name__]=module
        namespace=module.__dict__ if registered else {'__name__':module.__name__}
        filename=str(source.with_suffix(code_suffix))
        code=compile('import sys\nframe=sys._getframe()\ntry: 1/0\nexcept ZeroDivisionError as e: tb=e.__traceback__',filename,'exec');exec(code,namespace)
        for kind,obj in [('code',code),('frame',namespace['frame']),('traceback',namespace['tb'])]:
            case=repr((source_exists,module_suffix,code_suffix,registered,loader,override,kind))
            for name,m in mods.items():
                m.modulesbyfile.clear();m._filesbymodname.clear()
                args=() if override is None else (filename if override=='same' else str(source.with_suffix('.override')),)
                try:
                    value=m.getmodule(obj,*args)
                    value=value.__name__ if value else None
                except Exception as e:value='ERROR:'+type(e).__name__
                results[name][case]=value
        del sys.modules[module.__name__];namespace.pop('frame',None);namespace.pop('tb',None)
changes={name:{k:[results['main'][k],v] for k,v in results[name].items() if results['main'][k]!=v} for name in names[1:]}
(ROOT/'differential-results.json').write_text(json.dumps({'cases':len(results['main']),'differences_from_main':changes},indent=2))
print('Cases:',len(results['main']))
for name,changes in changes.items():
    print(name,len(changes));print(list(changes.items())[:5])
