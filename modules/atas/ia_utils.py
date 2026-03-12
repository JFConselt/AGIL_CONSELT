from google import genai
from google.genai import types
import typing_extensions as typing
import json
import pdfplumber
import streamlit as st
from modules.atas import config

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
                system_instruction=config.get_prompt_transparencias_system(),
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
                system_instruction=config.get_prompt_pautas_system(),
                temperature=0.3 # Mais determinístico para textos formais
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"Erro na geração: {str(e)}"

def refine_notices(text_content):
    """Padroniza e revisa os avisos gerais."""
    client = get_client()
    if not client:
        return text_content
    if not text_content or not str(text_content).strip():
        return ""

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

def _build_audit_context(context_dict):
    lines = []

    for pauta in context_dict.get("pautas", []):
        titulo = pauta.get("titulo") or "Pauta sem título"
        texto = (pauta.get("texto") or "").strip()
        excerpt = texto[:500] + ("..." if len(texto) > 500 else "")
        lines.append(f"PAUTA: {titulo}\n{excerpt}")

    transparencias = context_dict.get("transparencias", {})
    for diretoria, conteudo in transparencias.items():
        realizado = (conteudo.get("Realizado") or "")[:250]
        planejado = (conteudo.get("Planejado") or "")[:250]
        lines.append(f"TRANSPARENCIA {diretoria}: Realizado={realizado} | Planejado={planejado}")

    avisos = (context_dict.get("avisos") or "").strip()
    if avisos:
        lines.append(f"AVISOS: {avisos[:500]}{'...' if len(avisos) > 500 else ''}")

    return "\n\n".join(lines)


def audit_meeting_summary(context_data):
    """Gera um resumo curto das correções necessárias."""
    client = get_client()
    if not client:
        return "Auditoria indisponível."

    if isinstance(context_data, str):
        context_text = context_data
    else:
        context_text = _build_audit_context(context_data)

    prompt = f"""
    Atue como Auditor. Analise os dados desta Ata.
    Seja BREVE e DIRETO. Liste apenas o que precisa de atenção em tópicos curtos (máx 5 linhas).
    Se estiver tudo ok, diga "Nenhuma inconsistência grave encontrada."
    
    DADOS: {context_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except: return "Auditoria indisponível."


def _generate_json_response(client, prompt):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json'
        )
    )
    return json.loads(response.text)


def _normalize_pautas(client, pautas):
    payload = [
        {
            "id": pauta.get("id", ""),
            "titulo": pauta.get("titulo", ""),
            "texto": pauta.get("texto", ""),
        }
        for pauta in pautas
        if pauta.get("texto")
    ]
    if not payload:
        return []

    batches = []
    current_batch = []
    current_size = 0
    max_batch_size = 12000

    for item in payload:
        item_size = len(json.dumps(item, ensure_ascii=False))
        if current_batch and current_size + item_size > max_batch_size:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(item)
        current_size += item_size

    if current_batch:
        batches.append(current_batch)

    corrected_payload = []
    for batch in batches:
        prompt = f"""
        Você é um Editor de Texto Automático.
        Receba a lista JSON de pautas abaixo e reescreva apenas o campo 'texto' de cada item.
        Preserve 'id' e 'titulo' exatamente como vieram.
        Corrija gramática, clareza e formalidade, mantendo o tom de ata.
        Retorne apenas um JSON válido no mesmo formato de lista.

        JSON ENTRADA:
        {json.dumps(batch, ensure_ascii=False)}
        """
        corrected = _generate_json_response(client, prompt)
        if not isinstance(corrected, list):
            raise ValueError("A IA retornou um formato inválido para pautas.")
        corrected_payload.extend(corrected)

    return corrected_payload


def _normalize_transparencias(client, transparencias):
    if not transparencias:
        return {}

    prompt = f"""
    Você é um Editor de Texto Automático.
    Receba o JSON abaixo de transparências e reescreva apenas os campos 'Realizado' e 'Planejado'.
    Preserve as diretorias e a estrutura do JSON.
    Corrija gramática, clareza e formalidade, mantendo o tom de ata.
    Retorne apenas um JSON válido.

    JSON ENTRADA:
    {json.dumps(transparencias, ensure_ascii=False)}
    """
    corrected = _generate_json_response(client, prompt)
    if not isinstance(corrected, dict):
        raise ValueError("A IA retornou um formato inválido para transparências.")
    return corrected

def apply_auto_corrections(context_dict):
    """
    Reescreve os textos do JSON corrigindo português e formalidade.
    """
    client = get_client()
    if not client:
        return {"Erro": "API Key não configurada."}

    try:
        return {
            "pautas": _normalize_pautas(client, context_dict.get("pautas", [])),
            "transparencias": _normalize_transparencias(client, context_dict.get("transparencias", {})),
            "avisos": refine_notices(context_dict.get("avisos", "")),
        }
    except Exception as e:
        return {"Erro": str(e)}