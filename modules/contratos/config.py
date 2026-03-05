import os

MODULE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(MODULE_DIR, "data")
DEFAULT_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato.docx")
LEGACY_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato_ps.docx")
PARTNERS_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato_parcerias.docx")

CONTRACT_MODELS = {
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
