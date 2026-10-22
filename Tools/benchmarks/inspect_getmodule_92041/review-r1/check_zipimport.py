"""Standalone fresh-namespace zipimport regression check for every variant."""
import importlib, importlib.util, sys, tempfile, zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
source='import sys\ndef capture():\n    return sys._getframe()\n'
for variant in ['main','candidate','replacement','combined','replacement_fixed','combined_fixed']:
    spec=importlib.util.spec_from_file_location('inspect_'+variant,root/'variants'/(variant+'.py'))
    inspect=importlib.util.module_from_spec(spec);sys.modules[spec.name]=inspect;spec.loader.exec_module(inspect)
    with tempfile.TemporaryDirectory() as directory:
        archive=Path(directory)/'frames.zip'
        with zipfile.ZipFile(archive,'w') as file:file.writestr('_inspect_zipped.py',source)
        sys.path.insert(0,str(archive))
        try:
            module=importlib.import_module('_inspect_zipped')
            ns={};exec(compile(source,module.__file__,'exec'),ns)
            frame=ns['capture']()
            assert inspect.getmodule(frame) is module,variant
            assert inspect.getsource(frame)=='def capture():\n    return sys._getframe()\n',variant
            print(variant,'PASS')
        finally:
            sys.path.pop(0);sys.modules.pop('_inspect_zipped',None)
