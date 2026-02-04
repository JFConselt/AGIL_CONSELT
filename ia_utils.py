from google import genai
from google.genai import types
import typing_extensions as typing
import json
import pdfplumber
import streamlit as st
import config

# --- Inicialização do Cliente ---
def get_client():
    """Retorna uma instância do cliente configurada."""
    if "GOOGLE_API_KEY" in st.secrets:
        return genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    return None

# --- Schemas (Mantidos para Estruturação) ---
class AtividadeDiretoria(typing.TypedDict):
    Realizado: str
    Planejado: str

class TransparenciasSchema(typing.TypedDict):
    Projetos: AtividadeDiretoria
    Marketing: AtividadeDiretoria
    Negócios: AtividadeDiretoria
    JF: AtividadeDiretoria
    Parcerias: AtividadeDiretoria
    GP: AtividadeDiretoria
    Qualidade: AtividadeDiretoria
    Direx: AtividadeDiretoria

# --- Utils de Arquivo ---
def extract_text_from_pdf(pdf_file, max_pages=20):
    full_text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            if not pdf.pages: return None
            for page in pdf.pages[:max_pages]:
                txt = page.extract_text()
                if txt: full_text += txt + "\n"
        return full_text if full_text.strip() else None
    except:
        return None

# --- Funções de IA ---

def process_transparencies(text_content, user_notes=""):
    client = get_client()
    if not client: return {"Erro": "API Key não configurada."}

    prompt = f"""
    Converta os dados brutos abaixo para o padrão da Ata.
    CONTEXTO INPUT: {text_content[:30000] if text_content else "Apenas notas."}
    NOTAS: {user_notes}
    Se uma diretoria não tiver dados, preencha: "Não foram apresentadas atividades."
    """
    
    try:
        # Nova Sintaxe: client.models.generate_content
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_TRANSPARENCIAS_SYSTEM,
                response_mime_type='application/json',
                response_schema=TransparenciasSchema
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {"Erro": f"Falha na IA: {str(e)}"}

def process_pauta(pdf_text, user_notes, titulo_pauta="", previous_context=""):
    """
    Gera o texto da pauta usando Few-Shot Learning dinâmico.
    """
    client = get_client()
    if not client: return "Erro: API Key ausente."

    # Tratamento para PDF vazio/imagem
    if pdf_text is None: pdf_text = ""
    
    if not pdf_text.strip() and not user_notes.strip():
        inputs = f"TÍTULO: {titulo_pauta}\n(OBS: Usuário não forneceu detalhes. Gere texto genérico formal confirmando o debate do tema.)"
    else:
        inputs = f"TÍTULO: {titulo_pauta}\n"
        if pdf_text: inputs += f"CONTEÚDO DO PDF/SLIDES: {pdf_text[:30000]}\n"
        if user_notes: inputs += f"NOTAS DO USUÁRIO: {user_notes}\n"

    context_injection = ""
    if previous_context:
        context_injection = f"\n\nESTILO DE REFERÊNCIA (Atas Anteriores):\n{previous_context[:5000]}\n"

    prompt = f"""
    {context_injection}
    Escreva um parágrafo narrativo formal (3ª pessoa) para a Ata de Reunião baseado nos dados abaixo.
    Não use tópicos. Texto corrido.
    
    DADOS:
    {inputs}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_PAUTAS_SYSTEM,
                temperature=0.3 # Mais determinístico para textos formais
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"Erro na geração: {str(e)}"

def refine_notices(text_content):
    """Padroniza e revisa os avisos gerais."""
    client = get_client()
    prompt = f"""
    Atue como um Secretário Sênior. Revise e padronize os avisos abaixo.
    Mantenha tom formal e corporativo.
    Texto: {text_content}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except: return text_content

def audit_meeting_summary(context_json_str):
    """Gera um resumo curto das correções necessárias."""
    client = get_client()
    prompt = f"""
    Atue como Auditor. Analise os dados desta Ata.
    Seja BREVE e DIRETO. Liste apenas o que precisa de atenção em tópicos curtos (máx 5 linhas).
    Se estiver tudo ok, diga "Nenhuma inconsistência grave encontrada."
    
    DADOS: {context_json_str[:20000]}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except: return "Auditoria indisponível."

def apply_auto_corrections(context_dict):
    """
    Reescreve os textos do JSON corrigindo português e formalidade.
    """
    client = get_client()
    
    prompt = f"""
    Você é um Editor de Texto Automático.
    Analise o JSON abaixo contendo 'pautas', 'transparencias' e 'avisos'.
    Reescreva APENAS os valores de texto (chaves 'texto', 'Realizado', 'Planejado', 'avisos') corrigindo:
    1. Erros gramaticais.
    2. Formalidade (tom corporativo).
    3. Clareza.
    
    Mantenha a ESTRUTURA do JSON intacta. Não remova chaves.
    
    JSON ENTRADA:
    {json.dumps(context_dict, default=str, ensure_ascii=False)[:30000]}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {"Erro": str(e)}