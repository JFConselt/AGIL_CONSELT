import os

MODULE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(MODULE_DIR, "data")
DEFAULT_TEMPLATE_PATH = os.path.join(DATA_DIR, "modelo_contrato.docx")
TIMEZONE = "America/Sao_Paulo"
ESTADO_FERIADOS = "MG"
AUTHENTIQUE_URL = "https://api.autentique.com.br/v2/graphql"
