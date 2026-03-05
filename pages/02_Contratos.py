import importlib
import sys

module_name = "modules.contratos.page_contratos"
if module_name in sys.modules:
	importlib.reload(sys.modules[module_name])
else:
	importlib.import_module(module_name)
