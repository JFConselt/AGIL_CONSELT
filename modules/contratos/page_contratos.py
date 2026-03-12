import os
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st

from modules.contratos import authentique_utils
from modules.contratos import admin_utils
from modules.contratos import config
from modules.contratos import document_utils
from modules.ui.sidebar import render_sidebar

# Garantir que os arquivos de tempo de execução estejam inicializados
admin_utils.ensure_runtime_files()

# Configuracao da pagina e navegacao compartilhada
st.set_page_config(page_title="AGIL | Contratos", page_icon="📝", layout="wide")

render_sidebar(active_page="contratos")

st.title("📝 AGIL | Contratos")
st.caption("Preenchimento automático de contrato e envio para assinatura via Authentique.")

st.markdown("---")

# Secao 1: selecao do modelo de contrato
st.subheader("1) Modelo do documento")
available_models = {
    model_id: model_data
    for model_id, model_data in config.get_contract_models().items()
    if os.path.exists(model_data["template_path"])
}

if not available_models:
    st.error("Nenhum modelo de contrato encontrado em modules/contratos/data.")
    st.stop()

active_model_id = config.get_active_contract_model_id()

selected_model_id = st.selectbox(
    "Selecione o modelo de contrato",
    options=list(available_models.keys()),
    index=max(0, list(available_models.keys()).index(active_model_id)) if active_model_id in available_models else 0,
    format_func=lambda model_id: available_models[model_id]["label"],
)
selected_model = available_models[selected_model_id]
selected_template_path = selected_model["template_path"]

st.info(
    f"Modelo selecionado: {selected_model['label']}"
)

if selected_model["form_type"] != "prestacao_servicos":
    st.warning("A estrutura de preenchimento deste modelo ainda nao foi implementada.")
    st.stop()

# Secao 2: dados base e objeto do contrato
st.subheader("2) Dados base do contrato")
c1, c2 = st.columns(2)
numero_contrato = c1.text_input("Número do contrato", placeholder="Ex: 2000/2026")
atual_presidente = c2.text_input("Nome do(a) Diretor(a) Presidente")
data_contrato = date.today()
c1.text_input("Data de criacao do contrato", value=data_contrato.strftime("%d/%m/%Y"), disabled=True)
cpf_presidente = c2.text_input("CPF do Diretor(a) Presidente", placeholder="Ex: 000.000.000-00")

servico = st.text_area("Serviço contratado", height=80, placeholder="Ex: Website")
detalhes = st.text_area("Detalhes do serviço a ser realizado", height=120, placeholder="Informações da Proposta Comercial")

c3, c4 = st.columns(2)
prazo_execucao = c3.number_input("Prazo de execução do serviço (dias úteis)", min_value=0, step=1, format="%d")
tolerancia_atraso = c3.number_input("Tolerância de atraso do envio de materiais (dias úteis)", min_value=0, step=1, format="%d")
valor_num = c4.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
valor = document_utils.format_brl_value(valor_num)
valor_extenso = document_utils.currency_to_words_br(valor_num)
c4.text_input("Valor por extenso", value=valor_extenso, disabled=True)

# Secao 3: identificacao da contratada (PJ ou PF)
st.subheader("3) Tipo da CONTRATADA")
tipo_contratada = st.radio("Escolha o tipo", options=["Pessoa juridica (PJ)", "Pessoa fisica (PF)"], horizontal=True)

if tipo_contratada == "Pessoa juridica (PJ)":
    st.markdown("**Dados da empresa**")
    pj1, pj2 = st.columns(2)
    nome_pj = pj1.text_input("Nome da Empresa", placeholder="Ex: ABC LTDA ME")
    cnpj = pj2.text_input("CNPJ", placeholder="Ex: 00.000.000/0001-00")

    pj4, pj5, pj6, pj7 = st.columns(4)
    rua_pj = pj4.text_input("Rua / Avenida", placeholder="Ex: Av. Paulista, Rua das Flores", key="pj_rua")
    numero_pj = pj5.text_input("Número", placeholder="Ex: 1000", key="pj_numero")
    complemento_pj = pj6.text_input("Complemento", placeholder="Ex: Ap. 123", key="pj_complemento")
    bairro_pj = pj7.text_input("Bairro", placeholder="Ex: Centro", key="pj_bairro")

    pj8, pj9, pj10 = st.columns(3)
    cep_pj = pj8.text_input("CEP", placeholder="Ex: 00000-000", key="pj_cep")
    cidade_pj = pj9.text_input("Cidade", placeholder="Ex: São Paulo", key="pj_cidade")
    estado_pj = pj10.text_input("Estado", placeholder="Ex: SP", key="pj_estado")

    st.markdown("**Representante legal**")
    rp1, rp2, rp3 = st.columns(3)
    cargo_rep = rp1.text_input("Cargo", placeholder="Ex: Diretor")
    nome_rep = rp2.text_input("Nome", placeholder="Ex: João da Silva")
    nacionalidade_rep = rp3.text_input("Nacionalidade", placeholder="Ex: Brasileira")

    rp4, rp5, rp6 = st.columns(3)
    estado_civil_rep = rp4.text_input("Estado civil", placeholder="Ex: Solteiro(a)")
    profissao_rep = rp5.text_input("Profissão", placeholder="Ex: Engenheiro")
    cpf_rep = rp6.text_input("CPF", placeholder="Ex: 000.000.000-00")

    rp7, rp8 = st.columns(2)
    rg_rep = rp7.text_input("RG", placeholder="Ex: 00.000.000-0")
    email_rep = rp8.text_input("Email", placeholder="Ex: joao.silva@email.com")

    rp9, rp10, rp11, rp12 = st.columns(4)
    rua_rep = rp9.text_input("Rua / Avenida", placeholder="Ex: Av. Paulista", key="rep_rua")
    numero_rep = rp10.text_input("Número", placeholder="Ex: 1000", key="rep_numero")
    complemento_rep = rp11.text_input("Complemento", placeholder="Ex: Ap. 123", key="rep_complemento")
    bairro_rep = rp12.text_input("Bairro", placeholder="Ex: Centro", key="rep_bairro")

    rp13, rp14, rp15 = st.columns(3)
    cep_rep = rp13.text_input("CEP", placeholder="Ex: 00000-000", key="rep_cep")
    cidade_rep = rp14.text_input("Cidade", placeholder="Ex: São Paulo", key="rep_cidade")
    estado_rep = rp15.text_input("Estado", placeholder="Ex: São Paulo", key="rep_estado")
else:
    st.markdown("**Dados da pessoa fisica (mapeados nas tags de representante)**")
    pf1, pf2, pf3 = st.columns(3)
    nome_pf = pf1.text_input("Nome completo", placeholder="Ex: Maria Silva")
    cpf_pf = pf2.text_input("CPF", placeholder="Ex: 000.000.000-00")
    rg_pf = pf3.text_input("RG", placeholder="Ex: 00.000.000-0")

    pf4, pf5, pf6 = st.columns(3)
    nacionalidade_pf = pf4.text_input("Nacionalidade", placeholder="Ex: Brasileira")
    estado_civil_pf = pf5.text_input("Estado civil", placeholder="Ex: Solteiro(a)")
    profissao_pf = pf6.text_input("Profissão", placeholder="Ex: Enfermeira")

    pf7, pf8, pf9, pf10 = st.columns(4)
    rua_pf = pf7.text_input("Rua", placeholder="Ex: Rua das Flores")
    numero_pf = pf8.text_input("Número", placeholder="Ex: 1000")
    complemento_pf = pf9.text_input("Complemento", placeholder="Ex: Ap. 123")
    bairro_pf = pf10.text_input("Bairro", placeholder="Ex: Centro")

    pf11, pf12, pf13, pf14 = st.columns(4)
    cep_pf = pf11.text_input("CEP", placeholder="Ex: 00000-000")
    cidade_pf = pf12.text_input("Cidade", placeholder="Ex: São Paulo")
    estado_pf = pf13.text_input("Estado", placeholder="Ex: São Paulo")
    email_pf = pf14.text_input("Email", placeholder="Ex: maria.souza@email.com")

    nome_pj = ""
    cnpj = ""
    rua_pj = ""
    numero_pj = ""
    complemento_pj = ""
    bairro_pj = ""
    cep_pj = ""
    cidade_pj = ""
    estado_pj = ""

    cargo_rep = "Contratada"
    nome_rep = nome_pf
    nacionalidade_rep = nacionalidade_pf
    estado_civil_rep = estado_civil_pf
    profissao_rep = profissao_pf
    cpf_rep = cpf_pf
    rg_rep = rg_pf
    email_rep = email_pf
    rua_rep = rua_pf
    numero_rep = numero_pf
    complemento_rep = complemento_pf
    bairro_rep = bairro_pf
    cep_rep = cep_pf
    cidade_rep = cidade_pf
    estado_rep = estado_pf

# Secao 4: condicoes de pagamento (capitulo 9)
st.subheader("4) Meio de Pagamento")
payment_option = st.radio(
    "Qual das 3 formas de pagamento o cliente optou?",
    options=["À vista", "Entrada de 50%", "Parcelado"],
    horizontal=True,
)

valor_entrada = ""
valor_entrada_extenso = ""
valor_parcela = ""
valor_parcela_extenso = ""
dia_parcela_1 = ""
mes_parcela_1 = ""
dia_parcela_2 = ""
mes_parcela_2 = ""
qtd_parcelas = ""

if payment_option == "Entrada de 50%":
    pg1, pg2, pg3 = st.columns(3)
    qtd_parcelas_int = pg1.number_input("Quantidade de parcelas restantes", min_value=2, max_value=3, step=1, format="%d")

    total = Decimal(str(valor_num)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entrada_total = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    restante_total = (total - entrada_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parcela_valor = (restante_total / Decimal(qtd_parcelas_int)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    valor_entrada = document_utils.format_brl_value(entrada_total)
    valor_entrada_extenso = document_utils.currency_to_words_br(entrada_total)
    valor_parcela = document_utils.format_brl_value(parcela_valor)
    valor_parcela_extenso = document_utils.currency_to_words_br(parcela_valor)
    qtd_parcelas = str(qtd_parcelas_int)

    pg2.text_input("Valor da entrada (50%)", value=valor_entrada, disabled=True)
    pg3.text_input("Valor da entrada por extenso", value=valor_entrada_extenso, disabled=True)

    pg4, pg5 = st.columns(2)
    pg4.text_input("Valor de cada parcela restante", value=valor_parcela, disabled=True)
    pg5.text_input("Valor da parcela por extenso", value=valor_parcela_extenso, disabled=True)

if payment_option == "Parcelado":
    pg9, pg10, pg11 = st.columns(3)
    qtd_parcelas_int = pg9.number_input("Quantidade de parcelas", min_value=2, step=1, format="%d")

    total = Decimal(str(valor_num)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parcela_valor = (total / Decimal(qtd_parcelas_int)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    valor_parcela = document_utils.format_brl_value(parcela_valor)
    valor_parcela_extenso = document_utils.currency_to_words_br(parcela_valor)
    qtd_parcelas = str(qtd_parcelas_int)

    pg10.text_input("Valor da parcela", value=valor_parcela, disabled=True)
    pg11.text_input("Valor da parcela por extenso", value=valor_parcela_extenso, disabled=True)

# Secao 5: dados de testemunhas
st.subheader("5) Testemunhas")
t1, t2 = st.columns(2)
testemunha_1 = t1.text_input("1ª Testemunha", placeholder="Ex: Carlos Pereira")
testemunha_1_cpf = t1.text_input("CPF da 1ª Testemunha", placeholder="Ex: 123.456.789-00")
testemunha_2 = t2.text_input("2ª Testemunha", placeholder="Ex: Maria Silva")
testemunha_2_cpf = t2.text_input("CPF da 2ª Testemunha", placeholder="Ex: 987.654.321-00")

# Secao 6: signatarios para envio na Authentique
st.subheader("6) Signatarios (Authenique)")
s1, s2 = st.columns(2)
email_presidente_assinatura = s1.text_input(
    "Email do Diretor(a) Presidente",
    placeholder="Ex: presidente@conselt.com",
)
email_representante_assinatura = s2.text_input(
    "Email do Representante/Pessoa Fisica",
    value=email_rep,
    placeholder="Ex: representante@empresa.com",
)

s3, s4 = st.columns(2)
email_testemunha_1 = s3.text_input(
    "Email da 1ª Testemunha",
    placeholder="Ex: testemunha1@email.com",
)
email_testemunha_2 = s4.text_input(
    "Email da 2ª Testemunha",
    placeholder="Ex: testemunha2@email.com",
)

if "contract_file" not in st.session_state:
    st.session_state.contract_file = None

if "contract_filename" not in st.session_state:
    st.session_state.contract_filename = "contrato_preenchido.pdf"

# Geracao do DOCX preenchido a partir do modelo selecionado
if st.button("Gerar contrato preenchido", type="primary"):
    template_bytes = None

    if os.path.exists(selected_template_path):
        with open(selected_template_path, "rb") as template_file:
            template_bytes = template_file.read()

    if template_bytes is None:
        st.error("Nao foi possivel carregar o modelo selecionado.")
    else:
        form_data = {
            "tipo_contratada": "PJ" if tipo_contratada == "Pessoa juridica (PJ)" else "PF",
            "numero_contrato": numero_contrato,
            "atual_presidente": atual_presidente,
            "cpf_presidente": cpf_presidente,
            "nome_pj": nome_pj,
            "cnpj": cnpj,
            "rua_pj": rua_pj,
            "numero_pj": numero_pj,
            "complemento_pj": complemento_pj,
            "bairro_pj": bairro_pj,
            "cep_pj": cep_pj,
            "cidade_pj": cidade_pj,
            "estado_pj": estado_pj,
            "cargo_rep": cargo_rep,
            "nome_rep": nome_rep,
            "nacionalidade_rep": nacionalidade_rep,
            "estado_civil_rep": estado_civil_rep,
            "profissao_rep": profissao_rep,
            "cpf_rep": cpf_rep,
            "rg_rep": rg_rep,
            "email_rep": email_rep,
            "rua_rep": rua_rep,
            "numero_rep": numero_rep,
            "complemento_rep": complemento_rep,
            "bairro_rep": bairro_rep,
            "cep_rep": cep_rep,
            "cidade_rep": cidade_rep,
            "estado_rep": estado_rep,
            "servico": servico,
            "detalhes": detalhes,
            "prazo_execucao": prazo_execucao,
            "tolerancia_atraso": tolerancia_atraso,
            "valor": valor,
            "valor_extenso": valor_extenso,
            "opcao_pagamento": payment_option,
            "valor_entrada": valor_entrada,
            "valor_entrada_extenso": valor_entrada_extenso,
            "valor_parcela": valor_parcela,
            "valor_parcela_extenso": valor_parcela_extenso,
            "qtd_parcelas": qtd_parcelas,
            "dia_parcela_1": dia_parcela_1,
            "mes_parcela_1": mes_parcela_1,
            "dia_parcela_2": dia_parcela_2,
            "mes_parcela_2": mes_parcela_2,
            "data_contrato": data_contrato,
            "testemunha_1": testemunha_1,
            "testemunha_1_cpf": testemunha_1_cpf,
            "testemunha_2": testemunha_2,
            "testemunha_2_cpf": testemunha_2_cpf,
        }

        try:
            context = document_utils.build_context(form_data)
            rendered_doc = document_utils.render_contract(template_bytes, context)
            pdf_bytes = document_utils.convert_docx_bytes_to_pdf_bytes(rendered_doc.getvalue())
            st.session_state.contract_file = pdf_bytes
            contract_name = f"Contrato_{numero_contrato}.pdf" if numero_contrato else "Contrato_preenchido.pdf"
            st.session_state.contract_filename = contract_name
            st.success("Contrato gerado e convertido para PDF com sucesso.")
        except Exception as error:
            st.error(f"Erro ao gerar contrato: {error}")

# Download local e envio opcional para assinatura
if st.session_state.contract_file:
    st.download_button(
        "Baixar contrato .pdf",
        data=st.session_state.contract_file,
        file_name=st.session_state.contract_filename,
        mime="application/pdf",
    )

    if st.button("Enviar para Authentique"):
        signer_fields = [
            ("Diretor(a) Presidente", email_presidente_assinatura.strip()),
            ("Representante/Pessoa Fisica", email_representante_assinatura.strip()),
            ("1a Testemunha", email_testemunha_1.strip()),
            ("2a Testemunha", email_testemunha_2.strip()),
        ]

        missing_signers = [label for label, email in signer_fields if not email]
        if missing_signers:
            st.error("Preencha todos os emails dos signatarios antes de enviar para a Authentique.")
            st.write(missing_signers)
        else:
            signers = [{"email": email, "action": "SIGN"} for _, email in signer_fields]
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
