import json
from datetime import datetime, timedelta

import holidays
import pytz
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from modules.contratos import config


def _get_upload_mime_type(file_name):
    lower_name = file_name.lower()
    if lower_name.endswith(".pdf"):
        return "application/pdf"
    if lower_name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


def calculate_deadline():
    try:
        tz_local = pytz.timezone(config.TIMEZONE)
    except Exception:
        tz_local = pytz.timezone("America/Sao_Paulo")

    now = datetime.now(tz_local)

    try:
        br_holidays = holidays.Brazil(state=config.ESTADO_FERIADOS)
    except Exception:
        br_holidays = {}

    days_added = 0
    current_date = now

    while days_added < 2:
        current_date += timedelta(days=1)
        if current_date.weekday() >= 5:
            continue
        if current_date.date() in br_holidays:
            continue
        days_added += 1

    deadline_iso = current_date.replace(hour=23, minute=59, second=59, microsecond=999000)
    return deadline_iso.strftime("%Y-%m-%dT%H:%M:%S.999Z")


def send_to_authentique(file_bytes, file_name, signers, doc_name):
    if "AUTHENTIQUE_TOKEN" not in st.secrets:
        raise Exception("Token da Authentique não configurado em st.secrets['AUTHENTIQUE_TOKEN'].")

    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()

    query = """
    mutation CreateDocumentMutation($document: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!) {
        createDocument(document: $document, signers: $signers, file: $file) {
            id
            name
            deadline_at
        }
    }
    """

    variables = {
        "document": {
            "name": doc_name,
            "deadline_at": deadline,
        },
        "signers": [{"email": signer["email"], "action": signer["action"]} for signer in signers],
        "file": None,
    }

    operations = json.dumps({"query": query, "variables": variables})
    map_data = json.dumps({"0": ["variables.file"]})

    files = {
        "operations": (None, operations, "application/json"),
        "map": (None, map_data, "application/json"),
        "0": (file_name, file_bytes, _get_upload_mime_type(file_name)),
    }

    headers = {"Authorization": f"Bearer {token}"}

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    response = session.post(config.AUTHENTIQUE_URL, headers=headers, files=files, timeout=60)

    if response.status_code != 200:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

    data = response.json()
    if "errors" in data:
        raise Exception(json.dumps(data["errors"], indent=2, ensure_ascii=False))

    return data["data"]["createDocument"]
