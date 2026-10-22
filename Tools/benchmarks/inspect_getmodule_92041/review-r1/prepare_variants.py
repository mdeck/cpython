from pathlib import Path
root=Path('variants')
base=(root/'main.py').read_text()
candidate=(root/'candidate.py').read_text()
old='''    try:
        file = getabsfile(object, _filename)
'''
new='''    try:
        if _filename is None:
            _filename = getfile(object)
        file = getabsfile(object, _filename)
'''
for name,s in [('replacement',base),('combined',candidate)]:
    assert s.count(old)==1
    (root/(name+'.py')).write_text(s.replace(old,new))
# A prospective regression correction, kept outside our candidate's scope.
fixed='''    try:
        if _filename is None:
            _filename = getfile(object)
            if _filename.endswith(tuple(importlib.machinery.BYTECODE_SUFFIXES)):
                _filename = getsourcefile(object) or _filename
        file = getabsfile(object, _filename)
'''
for name,s in [('replacement_fixed',base),('combined_fixed',candidate)]:
    (root/(name+'.py')).write_text(s.replace(old,fixed))
