import json
import os

MODULE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(MODULE_DIR, "data")
DEFAULT_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato.docx")
LEGACY_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato_ps.docx")
PARTNERS_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato_parcerias.docx")
MANAGED_TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
TEMPLATE_REGISTRY_PATH = os.path.join(DATA_DIR, "template_registry.json")

DEFAULT_CONTRACT_MODELS = {
	"prestacao_servicos": {
		"label": "Contrato de Prestacao de Servicos",
		"template_path": LEGACY_TEMPLATE_PATH,
		"form_type": "prestacao_servicos",
	},
	"parcerias": {
		"label": "Contrato de Parcerias",
		"template_path": PARTNERS_TEMPLATE_PATH,
		"form_type": "parcerias",
	},
}

TIMEZONE = "America/Sao_Paulo"
ESTADO_FERIADOS = "MG"
AUTHENTIQUE_URL = "https://api.autentique.com.br/v2/graphql"


def _read_json(path, default):
	try:
		with open(path, "r", encoding="utf-8") as file_obj:
			return json.load(file_obj)
	except (FileNotFoundError, json.JSONDecodeError):
		return default


def _resolve_registry_path(path_value):
	if not path_value:
		return None
	# Aceita paths com '/' ou '\\' independentemente do SO onde o registro foi gerado.
	path_value = path_value.replace("\\", os.sep).replace("/", os.sep)
	if os.path.isabs(path_value):
		return os.path.normpath(path_value)
	return os.path.normpath(os.path.join(MODULE_DIR, path_value))


def get_contract_models():
	registry = _read_json(TEMPLATE_REGISTRY_PATH, {})
	templates = registry.get("templates", [])
	if not templates:
		return DEFAULT_CONTRACT_MODELS

	return {
		entry["id"]: {
			"label": entry["label"],
			"template_path": _resolve_registry_path(entry["template_path"]),
			"form_type": entry["form_type"],
		}
		for entry in templates
	}


def get_active_contract_model_id():
	registry = _read_json(TEMPLATE_REGISTRY_PATH, {})
	active_template = registry.get("active_template")
	if active_template:
		return active_template

	for model_id, model_data in DEFAULT_CONTRACT_MODELS.items():
		if os.path.exists(model_data["template_path"]):
			return model_id
	return next(iter(DEFAULT_CONTRACT_MODELS), None)


CONTRACT_MODELS = DEFAULT_CONTRACT_MODELS
