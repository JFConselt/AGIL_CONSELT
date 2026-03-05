import importlib
import sys

module_name = "modules.atas.page_atas"
if module_name in sys.modules:
	importlib.reload(sys.modules[module_name])
else:
	importlib.import_module(module_name)
