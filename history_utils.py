import os
from docx import Document
import streamlit as st

# Cache para não ler disco toda hora
@st.cache_data(show_spinner=False)
def load_reference_style(folder_path="exemplos_atas"):
    full_context = ""
    if not os.path.exists(folder_path): return "", 0
    
    files = [f for f in os.listdir(folder_path) if f.endswith(".docx") and not f.startswith("~$")]
    # Pega só os 3 últimos para economizar tokens
    for f in sorted(files, reverse=True)[:3]:
        try:
            doc = Document(os.path.join(folder_path, f))
            txt = " ".join([p.text for p in doc.paragraphs if p.text.strip()])
            full_context += f"--- {f} ---\n{txt}\n"
        except: pass
    return full_context, len(files)