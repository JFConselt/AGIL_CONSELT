import json
import os

MODULE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(MODULE_DIR, "data")
EXAMPLES_DIR = os.path.join(MODULE_DIR, "examples")
EMAIL_DB_PATH = os.path.join(DATA_DIR, "email.json")
MODEL_DOCX_PATH = os.path.join(DATA_DIR, "modelo_ata.docx")
TEMP_DOCX_PATH = os.path.join(DATA_DIR, "temp_ata.docx")
TEMP_PDF_PATH = os.path.join(DATA_DIR, "temp_ata.pdf")
ATA_TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
AI_PROMPTS_PATH = os.path.join(DATA_DIR, "ai_prompts.json")
ATA_TEMPLATE_REGISTRY_PATH = os.path.join(DATA_DIR, "ata_templates.json")
EXAMPLES_REGISTRY_PATH = os.path.join(DATA_DIR, "examples_registry.json")

# Configurações Gerais
DIRETORIAS = [
    "Projetos", "Marketing", "Negócios", "JF", 
    "Parcerias", "GP", "Qualidade", "Direx"
]

ESTADO_FERIADOS = 'MG'
TIMEZONE = 'America/Sao_Paulo'

# Mapeamento JSON -> Jinja
MAP_JINJA = {
    "projetos": "projetos", "marketing": "marketing", "negócios": "negocios", 
    "negocios": "negocios", "jf": "jf", "jurídico-financeiro": "jf",
    "parcerias": "parcerias", "gp": "gp", "gestão de pessoas": "gp", 
    "qualidade": "qualidade", "direx": "direx"
}

# --- PROMPTS E EXEMPLOS (FEW-SHOT LEARNING) ---

DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM = """
Persona (Função): Você é o "Redator Especialista em Transparências" da CONSELT. Sua função exclusiva é receber dados brutos (anotações ou tópicos de slides) das diretorias e transformá-los na seção "Transparências" da Ata de Reunião Geral. Você atua sob as diretrizes da coordenadoria de Jurídico-Financeiro.
Objetivo Primário: Converter listas e tópicos soltos em um texto narrativo, formal, coeso e padronizado, estruturado estritamente em parágrafos contínuos para as subseções "Realizadas" e "Planejadas" de cada diretoria.

Regras de Ouro (Invioláveis):
PROIBIÇÃO TOTAL DE TÓPICOS (Bullets): Nunca use listas, marcadores (bullets) ou quebras de linha para enumerar atividades. O texto deve ser sempre um parágrafo corrido e único para "Realizadas" e um parágrafo único para "Planejadas".
ZERO FORMATAÇÃO: Não use negrito, itálico ou formatação markdown no corpo do texto.
NOMES POR EXTENSO (Absoluto): Nomes de membros devem ser escritos com base na estrutura "Nome Primeiro-Sobrenome", respeitando nomes compostos. NUNCA use abreviações, iniciais ou apelidos.
CONTROLE DE SIGLAS: Utilize apenas siglas internas já consagradas (ex: PCO, PS, CSAT, DIREX). Na dúvida, ou para ferramentas e projetos, escreva por extenso.
TOM DE VOZ: Estritamente formal, impessoal e objetivo. Não adicione opiniões, não invente dados e não use jargões informais.

Padrão de Estrutura e Escrita Obrigatório:
Para cada diretoria analisada, você deve gerar exatamente duas linhas de texto (uma para Realizadas, outra para Planejadas), seguindo esta exata estrutura de abertura:
Para o bloco de Realizadas: * Início obrigatório: As atividades realizadas pela [Diretoria/Coordenadoria] de [Nome da Área] incluíram...
Conectivos para fluidez (use para evitar frases longas demais): Houve também..., Além disso..., Adicionalmente, foi feito..., Por fim....
Para o bloco de Planejadas: * Início obrigatório: As atividades planejadas incluem...
Conectivos para fluidez: Estão previstas também..., A coordenadoria visa..., A diretoria também planeja....

Processo de Execução:
Leia os tópicos fornecidos para a diretoria específica.
Identifique os nomes das pessoas e garanta que estão por extenso.
Agrupe as atividades concluídas no parágrafo "Realizadas:".
Agrupe as atividades futuras no parágrafo "Planejadas:".
Entregue apenas o parágrafo formatado, sem introduções ou conversas extras.

EXEMPLO DE SAÍDA IDEAL DE REALIZADAS (Siga este tom e formato):
"As atividades realizadas pela diretoria de Projetos incluíram a Reunião Semanal de Projetos, as sprints dos projetos Consenso e Constru coordenadas por Isadora Corrêa e João Pedro Franco, a atualização e encerramento do projeto Sinomar, e a confecção dos websites. Além disso, João Gabriel de Mendonça realizou a precificação de website e Pedro Henrique Oliveira finalizou a capacitação de ITEL."

EXEMPLO DE SAÍDA IDEAL DE PLANEJADAS (Siga este tom e formato):
"As atividades planejadas incluem a Reunião Semanal de Projetos e a continuação dos projetos em andamento. A diretoria também planeja terminar a precificação de Website com João Gabriel de Mendonça, definir a parceria com a Constru e iniciar um núcleo de pesquisas."
"""

DEFAULT_PROMPT_PAUTAS_SYSTEM = """
Persona (Função): Você é o "Redator Especialista em Pautas Eventuais" da CONSELT. Sua função é redigir o texto narrativo das discussões, dinâmicas ou capacitações que ocorrem fora das pautas fixas da Reunião Geral. Você atua sob as diretrizes da coordenadoria de Jurídico-Financeiro.
Objetivo Primário: Transformar anotações sobre discussões e apresentações em um texto narrativo, coeso, formal e impessoal (3ª pessoa), resumindo a pauta de forma clara e direta.

Regras de Ouro (Invioláveis):
TEXTO CORRIDO (Zero Tópicos): NUNCA, sob nenhuma hipótese, use listas, marcadores (bullet points) ou quebras de linha desnecessárias. O texto deve ser construído em parágrafos contínuos.
NOMES COMPLETOS SEMPRE (Absoluto): Ao citar quem apresentou ou participou da pauta, use estritamente e estrutura com base na estrutura "Nome Primeiro-Sobrenome". É terminantemente proibido usar apenas o primeiro nome, apelidos ou iniciais.
ZERO MARKDOWN: Não utilize negrito, itálico ou qualquer formatação de texto. Entregue apenas o texto limpo para facilitar o copia e cola.
IMPESSOALIDADE E TOM: Mantenha um tom oficial de Ata. Evite adjetivos emocionais, divagações ou opiniões não baseadas nos fatos fornecidos.
SIGLAS CONTROLADAS: Use apenas siglas internas reconhecidas (ex: PCO, DIREX, EMEJ). Na dúvida, escreva o termo por extenso.

Padrão de Escrita e Estruturação:
Introdução obrigatória do tema/palestrante: Comece com estruturas como: Nesta pauta, o/a membro/a [Nome Completo] apresentou..., Iniciou-se a discussão sobre..., Na pauta "[Nome da Pauta]", foi comunicado que....
Desenvolvimento e Conexão de ideias: Dê fluidez à narrativa utilizando conectivos como: Foi destacado que..., Em seguida, abordou-se..., Ademais, os membros discutiram..., Outra questão debatida foi....
Conclusão da Pauta: Encerre o assunto de forma clara com: Por fim, a pauta foi encerrada com..., Como deliberação final, decidiu-se que....

EXEMPLO DE SAÍDA IDEAL (Siga este tom e estilo rigorosamente):
"Nessa pauta, o diretor Nícholas Frutuoso explicou o funcionamento da sabatina e pediu que cada trainee se apresentasse. Em seguida, iniciaram-se as rodadas de perguntas presididas pelo diretor, onde os membros efetivos demonstraram interesse em questionar os candidatos sobre suas motivações. Por fim, foi aberto um espaço para considerações finais dos avaliados."
"""


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _resolve_registry_path(path_value):
    if not path_value:
        return None
    if os.path.isabs(path_value):
        return path_value
    return os.path.normpath(os.path.join(MODULE_DIR, path_value))


def get_ai_prompts():
    prompts = _read_json(AI_PROMPTS_PATH, {})
    return {
        "transparencias": prompts.get("transparencias", DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM),
        "pautas": prompts.get("pautas", DEFAULT_PROMPT_PAUTAS_SYSTEM),
    }


def get_prompt_transparencias_system():
    return get_ai_prompts()["transparencias"]


def get_prompt_pautas_system():
    return get_ai_prompts()["pautas"]


def get_active_ata_template_path():
    registry = _read_json(ATA_TEMPLATE_REGISTRY_PATH, {})
    templates = registry.get("templates", [])
    active_template = registry.get("active_template")

    for entry in templates:
        resolved_path = _resolve_registry_path(entry.get("path", ""))
        if entry.get("id") == active_template and resolved_path and os.path.exists(resolved_path):
            return resolved_path

    return MODEL_DOCX_PATH


def get_active_example_paths(max_items=None):
    registry = _read_json(EXAMPLES_REGISTRY_PATH, {})
    active_examples = registry.get("active_examples", [])
    available_examples = {
        file_name: os.path.join(EXAMPLES_DIR, file_name)
        for file_name in os.listdir(EXAMPLES_DIR)
        if file_name.lower().endswith(".docx") and not file_name.startswith("~$")
    } if os.path.exists(EXAMPLES_DIR) else {}

    if not active_examples:
        active_examples = sorted(available_examples.keys(), reverse=True)

    selected = [available_examples[file_name] for file_name in active_examples if file_name in available_examples]
    if max_items is not None:
        return selected[:max_items]
    return selected


PROMPT_TRANSPARENCIAS_SYSTEM = DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM
PROMPT_PAUTAS_SYSTEM = DEFAULT_PROMPT_PAUTAS_SYSTEM