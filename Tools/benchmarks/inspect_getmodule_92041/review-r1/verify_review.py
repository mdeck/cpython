import importlib.util, io, unittest
from pathlib import Path
from test.test_inspect import test_inspect
root = Path(__file__).resolve().parent
for variant in ('before', 'after'):
    spec = importlib.util.spec_from_file_location('review_' + variant, root / 'variants' / (variant + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    test_inspect.inspect = module
    output = io.StringIO()
    suite = unittest.TestSuite([test_inspect.TestGetmoduleFrameOwner('test_static_filename_with_module_getattr_avoids_scan')])
    result = unittest.TextTestRunner(stream=output).run(suite)
    if variant == 'before':
        assert len(result.failures) == 1 and not result.errors, output.getvalue()
        assert 'registered frame scanned sys.modules' in result.failures[0][1]
        print('Old guard: new no-scan regression test fails for the expected registry scan')
    else:
        assert result.wasSuccessful(), output.getvalue()
        print('Revised guard: new no-scan regression test passes')
    names = ('test_filename_supplied_by_module_getattr_falls_back', 'test_loader_supplied_by_module_getattr', 'test_dynamic_module_metadata_falls_back')
    suite = unittest.TestSuite(test_inspect.TestGetmoduleFrameOwner(name) for _ in range(50) for name in names)
    result = unittest.TextTestRunner().run(suite)
    assert result.wasSuccessful()
    print(variant, '150 repeated dynamic filename/loader/subclass tests passed')
