import requests
import json
import difflib
from datetime import datetime, timedelta
import streamlit as st
import pytz
import holidays
import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def calculate_deadline():
    """Calcula data de bloqueio (deadline) em ISO 8601."""
    try:
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
    except:
        now = datetime.now()
    
    # Tenta carregar feriados
    try:
        br_holidays = holidays.Brazil(state=config.ESTADO_FERIADOS)
    except:
        br_holidays = {}

    days_added = 0
    current_date = now
    
    while days_added < 2:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5 and current_date not in br_holidays:
            days_added += 1
            
    deadline = current_date.replace(hour=23, minute=59, second=59)
    # O método isoformat() é mais seguro que strftime para APIs
    return deadline.isoformat()

def get_signers_emails(names_text, emails_db_path='email.json'):
    try:
        with open(emails_db_path, 'r', encoding='utf-8') as f:
            db_emails = json.load(f)
    except FileNotFoundError:
        return [], ["Erro: Arquivo email.json não encontrado"], []

    raw_names = [n.strip().rstrip('.') for n in names_text.split('\n') if n.strip()]
    signers = []
    missing = []
    display_map = []
    
    known_names = list(db_emails.keys())

    for name in raw_names:
        if name in db_emails:
            email = db_emails[name]
            signers.append({"email": email, "action": "SIGN"})
            display_map.append((name, email, "Exato"))
            continue
            
        matches = difflib.get_close_matches(name, known_names, n=1, cutoff=0.6)
        if matches:
            matched_name = matches[0]
            email = db_emails[matched_name]
            signers.append({"email": email, "action": "SIGN"})
            display_map.append((name, email, f"Aproximado de '{matched_name}'"))
        else:
            missing.append(name)
            display_map.append((name, "❌ NÃO ENCONTRADO", "Erro"))

    return signers, missing, display_map

def send_to_authentique(file_obj, signers, doc_name="ATA de Reunião"):
    """
    Envia para API Authentique seguindo o padrão Multipart Form Data.
    Corrige o argumento da mutation para 'attributes'.
    """
    
    url = "https://api.authentique.com.br/v2/graphql"
    
    if "AUTHENTIQUE_TOKEN" not in st.secrets:
        raise Exception("Token da Authentique não configurado no secrets.")
        
    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()
    
    # --- CORREÇÃO: O padrão da API é 'attributes' ---
    # Se a sua documentação específica exigir 'document', reverta essa mudança.
    query = """
    mutation CreateDocumentMutation($attributes: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!) {
        createDocument(attributes: $attributes, signers: $signers, file: $file) {
            id
            name
            deadline_at
        }
    }
    """
    
    # As variáveis devem refletir os nomes usados na query acima ($attributes)
    variables = {
        "attributes": {
            "name": doc_name,
            "deadline_at": deadline
        },
        "signers": signers,
        "file": None
    }
    
    # Preparação do Multipart (Padrão GraphQL)
    operations = json.dumps({"query": query, "variables": variables})
    map_data = json.dumps({"0": ["variables.file"]})
    
    # Importante: Garantir que o ponteiro do arquivo está no início
    file_obj.seek(0)
    
    files = {
        "operations": (None, operations, "application/json"),
        "map": (None, map_data, "application/json"),
        "0": (doc_name, file_obj, "application/pdf")
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
        # Não adicione 'Content-Type': 'multipart/form-data' aqui manualmente! 
        # A lib requests faz isso automaticamente com o boundary correto.
    }
    
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        response = session.post(url, headers=headers, files=files, timeout=60)
        
        # Debug: Se der erro 400, imprime o que a API respondeu
        if response.status_code != 200:
            error_msg = response.text
            try:
                error_json = response.json()
                if "errors" in error_json:
                    error_msg = json.dumps(error_json["errors"], indent=2, ensure_ascii=False)
            except:
                pass
            raise Exception(f"Erro API ({response.status_code}): {error_msg}")
            
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"Erro Retornado pela Authentique: {json.dumps(data['errors'], indent=2, ensure_ascii=False)}")
            
        return data["data"]["createDocument"]["id"]
        
    except requests.exceptions.ConnectionError:
        raise Exception("Erro de Conexão: Falha ao resolver DNS ou conectar à Authentique.")
    except Exception as e:
        raise Exception(f"Falha no envio: {str(e)}")