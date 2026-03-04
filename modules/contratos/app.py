import os

import streamlit as st

from modules.contratos import authentique_utils
from modules.contratos import config
from modules.contratos import document_utils
from modules.ui.sidebar import render_sidebar

st.set_page_config(page_title="AGIL | Contratos", page_icon="📝", layout="wide")

render_sidebar(active_page="contratos")

st.title("📝 AGIL | Contratos")
st.caption("Preenchimento automático de contrato e envio para assinatura via Authentique.")

if st.button("⬅️ Voltar para início"):
    st.switch_page("app.py")

st.markdown("---")

st.subheader("1) Modelo do documento")
use_default_template = st.checkbox("Usar modelo padrão em modules/contratos/data/modelo_contrato.docx", value=True)
uploaded_template = st.file_uploader("Ou envie um modelo .docx", type=["docx"])

st.info(
    "Campos esperados no modelo DOCX (Jinja): {{ numero_contrato }}, {{ contratante }}, {{ contratado }}, {{ objeto }}, {{ valor }}, {{ data_contrato }}, {{ observacoes }}"
)

st.subheader("2) Dados do contrato")
col1, col2 = st.columns(2)
numero_contrato = col1.text_input("Número do contrato", placeholder="Ex: CTR-2026-001")
data_contrato = col2.date_input("Data do contrato")
contratante = col1.text_input("Contratante")
contratado = col2.text_input("Contratado")
objeto = st.text_area("Objeto do contrato", height=100)
valor = st.text_input("Valor", placeholder="Ex: R$ 15.000,00")
observacoes = st.text_area("Observações", height=100)

st.subheader("3) Signatários")
signers_text = st.text_area(
    "Informe um signatário por linha no formato: Nome;email",
    placeholder="João Silva;joao@email.com\\nMaria Souza;maria@email.com",
    height=120,
)

if "contract_file" not in st.session_state:
    st.session_state.contract_file = None

if "contract_filename" not in st.session_state:
    st.session_state.contract_filename = "contrato_preenchido.docx"

if st.button("Gerar contrato preenchido", type="primary"):
    template_bytes = None

    if uploaded_template is not None:
        template_bytes = uploaded_template.getvalue()
    elif use_default_template and os.path.exists(config.DEFAULT_TEMPLATE_PATH):
        with open(config.DEFAULT_TEMPLATE_PATH, "rb") as template_file:
            template_bytes = template_file.read()

    if template_bytes is None:
        st.error("Envie um modelo .docx ou adicione o modelo padrão em modules/contratos/data/modelo_contrato.docx")
    else:
        context = {
            "numero_contrato": numero_contrato,
            "contratante": contratante,
            "contratado": contratado,
            "objeto": objeto,
            "valor": valor,
            "data_contrato": data_contrato,
            "observacoes": observacoes,
        }

        try:
            rendered_doc = document_utils.render_contract(template_bytes, context)
            st.session_state.contract_file = rendered_doc.getvalue()
            contract_name = f"Contrato_{numero_contrato}.docx" if numero_contrato else "Contrato_preenchido.docx"
            st.session_state.contract_filename = contract_name
            st.success("Contrato gerado com sucesso.")
        except Exception as error:
            st.error(f"Erro ao gerar contrato: {error}")

if st.session_state.contract_file:
    st.download_button(
        "Baixar contrato .docx",
        data=st.session_state.contract_file,
        file_name=st.session_state.contract_filename,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    if st.button("Enviar para Authentique"):
        signers, invalid_lines = document_utils.parse_signers(signers_text)

        if invalid_lines:
            st.error("As linhas abaixo estão inválidas. Use o formato Nome;email:")
            st.write(invalid_lines)
        elif not signers:
            st.error("Informe ao menos um signatário válido.")
        else:
            try:
                response = authentique_utils.send_to_authentique(
                    file_bytes=st.session_state.contract_file,
                    file_name=st.session_state.contract_filename,
                    signers=signers,
                    doc_name=numero_contrato or "Contrato CONSELT",
                )
                st.success("Documento enviado para Authentique com sucesso.")
                st.write(f"ID do documento: {response['id']}")
                st.write(f"Nome: {response['name']}")
                st.write(f"Prazo: {response['deadline_at']}")
            except Exception as error:
                st.error(f"Falha no envio para Authentique: {error}")
