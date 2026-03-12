import io
import re
import os
import tempfile
import zipfile
import subprocess
import platform
import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from docxtpl import DocxTemplate


TAG_ALIASES = {
    "numero contrato": "numero_contrato",
    "atual presidente": "atual_presidente",
    "rg rep": "rg_rep",
    "opcao pagamento": "opcao_pagamento",
    "opcao escolhida": "opcao_pagamento",
}


BASE_TAGS = [
    "numero_contrato",
    "atual_presidente",
    "cpf_presidente",
    "nome_pj",
    "cnpj",
    "rua_pj",
    "numero_pj",
    "complemento_pj",
    "bairro_pj",
    "cep_pj",
    "cidade_pj",
    "estado_pj",
    "cargo_rep",
    "nome_rep",
    "nacionalidade_rep",
    "estado_civil_rep",
    "profissao_rep",
    "cpf_rep",
    "rg_rep",
    "email_rep",
    "rua_rep",
    "numero_rep",
    "complemento_rep",
    "bairro_rep",
    "cep_rep",
    "cidade_rep",
    "estado_rep",
    "servico",
    "detalhes",
    "prazo_execucao",
    "tolerancia_atraso",
    "valor",
    "valor_extenso",
    "opcao_pagamento",
    "condicao",
    "valor_entrada",
    "valor_entrada_extenso",
    "dia",
    "mes",
    "ano",
    "testemunha_1",
    "testemunha_1_cpf",
    "testemunha_2",
    "testemunha_2_cpf",
]


MONTHS_PT_BR = {
    1: "janeiro",
    2: "fevereiro",
    3: "marco",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


UNITS_0_TO_19 = [
    "zero",
    "um",
    "dois",
    "tres",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
    "dez",
    "onze",
    "doze",
    "treze",
    "quatorze",
    "quinze",
    "dezesseis",
    "dezessete",
    "dezoito",
    "dezenove",
]

TENS = [
    "",
    "",
    "vinte",
    "trinta",
    "quarenta",
    "cinquenta",
    "sessenta",
    "setenta",
    "oitenta",
    "noventa",
]

HUNDREDS = [
    "",
    "cento",
    "duzentos",
    "trezentos",
    "quatrocentos",
    "quinhentos",
    "seiscentos",
    "setecentos",
    "oitocentos",
    "novecentos",
]


def format_value(value):
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return value


def format_brl_value(value):
    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    formatted = f"{decimal_value:,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _number_to_words_0_999(number):
    if number == 0:
        return ""
    if number == 100:
        return "cem"
    if number < 20:
        return UNITS_0_TO_19[number]
    if number < 100:
        tens = number // 10
        remainder = number % 10
        if remainder == 0:
            return TENS[tens]
        return f"{TENS[tens]} e {UNITS_0_TO_19[remainder]}"

    hundreds = number // 100
    remainder = number % 100
    if remainder == 0:
        return HUNDREDS[hundreds]
    return f"{HUNDREDS[hundreds]} e {_number_to_words_0_999(remainder)}"


def _integer_to_words_pt_br(number):
    if number == 0:
        return "zero"

    scales = [
        (1_000_000_000, "bilhao", "bilhoes"),
        (1_000_000, "milhao", "milhoes"),
        (1_000, "mil", "mil"),
        (1, "", ""),
    ]

    parts = []
    remainder = number

    for scale_value, singular, plural in scales:
        group = remainder // scale_value
        remainder = remainder % scale_value
        if group == 0:
            continue

        if scale_value == 1_000:
            if group == 1:
                parts.append("mil")
            else:
                parts.append(f"{_number_to_words_0_999(group)} mil")
            continue

        group_text = _number_to_words_0_999(group)
        if scale_value == 1:
            parts.append(group_text)
        elif group == 1:
            parts.append(f"{group_text} {singular}")
        else:
            parts.append(f"{group_text} {plural}")

    return " e ".join([part for part in parts if part])


def currency_to_words_br(value):
    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    integer_part = int(decimal_value)
    cents_part = int((decimal_value - Decimal(integer_part)) * 100)

    reais_text = _integer_to_words_pt_br(integer_part)
    if integer_part == 1:
        reais_text = f"{reais_text} real"
    else:
        reais_text = f"{reais_text} reais"

    if cents_part == 0:
        return reais_text

    cents_text = _integer_to_words_pt_br(cents_part)
    if cents_part == 1:
        cents_text = f"{cents_text} centavo"
    else:
        cents_text = f"{cents_text} centavos"

    return f"{reais_text} e {cents_text}"


def _normalize_template_tags(template_bytes):
    """Normaliza placeholders que venham com espacos (ex.: {{ numero contrato }})."""
    source = io.BytesIO(template_bytes)
    target = io.BytesIO()

    with zipfile.ZipFile(source, "r") as source_zip, zipfile.ZipFile(target, "w") as target_zip:
        for item in source_zip.infolist():
            content = source_zip.read(item.filename)

            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                xml_text = content.decode("utf-8")
                for original, alias in TAG_ALIASES.items():
                    xml_text = xml_text.replace(f"{{{{ {original} }}}}", f"{{{{ {alias} }}}}")

                # Suporta placeholder legado com parenteses duplos: (( campo )) -> {{ campo }}
                xml_text = re.sub(r"\(\(\s*([^()]+?)\s*\)\)", r"{{ \1 }}", xml_text)

                # Suporta placeholder com chaves quebradas: { { campo } } -> {{ campo }}
                xml_text = re.sub(r"\{\s*\{\s*([^{}]+?)\s*\}\s*\}", r"{{ \1 }}", xml_text)

                # Normaliza qualquer variavel Jinja com espacos para o padrao underscore.
                # Exemplo: {{ rg rep }} -> {{ rg_rep }}
                def normalize_var(match):
                    raw_name = match.group(1).strip()
                    normalized_name = re.sub(r"\s+", "_", raw_name)
                    return f"{{{{ {normalized_name} }}}}"

                # Aceita nomes com acentos e outros caracteres validos em labels legadas.
                xml_text = re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", normalize_var, xml_text)
                content = xml_text.encode("utf-8")

            target_zip.writestr(item, content)

    target.seek(0)
    return target.getvalue()


def build_payment_condition(payment_data):
    option = payment_data.get("opcao_pagamento", "")
    valor = payment_data.get("valor", "")
    valor_extenso = payment_data.get("valor_extenso", "")

    if option in ("A vista", "À vista"):
        return (
            "Pela prestacao dos servicos a CONTRATANTE pagara a CONTRATADA a quantia total de "
            f"R$ {valor} ({valor_extenso}), a vista, em ate 5 (cinco) dias uteis apos a assinatura do contrato."
        )

    if option == "Entrada de 50%":
        qtd_parcelas = payment_data.get("qtd_parcelas", "")
        valor_entrada = payment_data.get("valor_entrada", "")
        valor_entrada_extenso = payment_data.get("valor_entrada_extenso", "")
        valor_parcela = payment_data.get("valor_parcela", "")
        valor_parcela_extenso = payment_data.get("valor_parcela_extenso", "")

        return (
            "Pela prestacao dos servicos a CONTRATANTE pagara a CONTRATADA a quantia total de "
            f"R$ {valor} ({valor_extenso}), devendo ser paga a entrada de 50% do valor, R$ {valor_entrada} "
            f"({valor_entrada_extenso}), em ate 5 (cinco) dias uteis apos a assinatura do contrato. "
            f"O valor restante sera pago em {qtd_parcelas} parcelas mensais iguais de "
            f"R$ {valor_parcela} ({valor_parcela_extenso}) cada."
        )

    if option == "Parcelado":
        qtd_parcelas = payment_data.get("qtd_parcelas", "")
        valor_parcela = payment_data.get("valor_parcela", "")
        valor_parcela_extenso = payment_data.get("valor_parcela_extenso", "")

        return (
            "Pela prestacao dos servicos, a CONTRATANTE pagara a CONTRATADA a quantia total de "
            f"R$ {valor} ({valor_extenso}), em {qtd_parcelas} parcelas iguais com valor de "
            f"R$ {valor_parcela} ({valor_parcela_extenso})."
        )

    return ""


def build_context(form_data):
    context = {tag: "" for tag in BASE_TAGS}

    for key, value in form_data.items():
        if key in context:
            context[key] = value

    contract_date = form_data.get("data_contrato")
    if isinstance(contract_date, date):
        context["dia"] = f"{contract_date.day:02d}"
        context["mes"] = MONTHS_PT_BR.get(contract_date.month, "")
        context["ano"] = str(contract_date.year)

    context["condicao"] = build_payment_condition(form_data)

    # Aliases para compatibilidade com modelos antigos/alternativos.
    context["opcao"] = context.get("opcao_pagamento", "")
    context["rg"] = context.get("rg_rep", "")

    # Flags de apoio para blocos condicionais do template (PF/PJ)
    kind = form_data.get("tipo_contratada", "PJ")
    context["is_pj"] = kind == "PJ"
    context["is_pf"] = kind == "PF"
    context["pj"] = context["is_pj"]
    context["pf"] = context["is_pf"]

    return context


def render_contract(template_bytes, context):
    normalized_template = _normalize_template_tags(template_bytes)
    template_stream = io.BytesIO(normalized_template)
    document = DocxTemplate(template_stream)

    normalized_context = {key: format_value(value) for key, value in context.items()}
    document.render(normalized_context)

    output = io.BytesIO()
    document.save(output)
    output.seek(0)
    return output


def convert_docx_bytes_to_pdf_bytes(docx_bytes):
    """
    Converte bytes de DOCX para PDF usando LibreOffice em modo headless.
    """
    import streamlit as st
    
    with tempfile.TemporaryDirectory() as temp_dir:
        input_docx_path = os.path.join(temp_dir, "contrato_temp.docx")
        output_pdf_path = os.path.join(temp_dir, "contrato_temp.pdf")

        # Salvar DOCX temporário
        with open(input_docx_path, "wb") as docx_file:
            docx_file.write(docx_bytes)

        # Determinar comando LibreOffice baseado no SO
        system = platform.system()
        
        if system == "Windows":
            # Tentar encontrar LibreOffice no Windows
            libreoffice_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            libreoffice_cmd = None
            for path in libreoffice_paths:
                if os.path.exists(path):
                    libreoffice_cmd = path
                    break
            
            if not libreoffice_cmd:
                # Tentar usar 'soffice' do PATH
                try:
                    subprocess.run(["soffice", "--version"], capture_output=True, check=True, timeout=5)
                    libreoffice_cmd = "soffice"
                except:
                    raise Exception(
                        "LibreOffice não encontrado. Por favor, instale LibreOffice em: "
                        "https://www.libreoffice.org/download/ ou adicione ao PATH."
                    )
        else:
            # Para Linux/Mac, assumir que 'soffice' está no PATH
            libreoffice_cmd = "soffice"

        try:
            # Converter DOCX para PDF usando LibreOffice
            command = [
                libreoffice_cmd,
                "--headless",
                "--safe-mode",
                "--convert-to", "pdf",
                "--outdir", temp_dir,
                input_docx_path
            ]
            
            st.write(f"🔄 Convertendo documento para PDF... (pode levar alguns segundos)")
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            
            # Aguardar um pouco para garantir que o arquivo foi escrito
            time.sleep(2)
            
            # Log detalhado
            debug_info = {
                "returncode": result.returncode,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "files_in_temp": os.listdir(temp_dir),
                "pdf_path_exists": os.path.exists(output_pdf_path)
            }
            st.write(f"📋 Debug: {debug_info}")
            
            if result.returncode != 0:
                error_msg = f"LibreOffice retornou erro: {result.stderr or result.stdout or 'Erro desconhecido'}"
                st.error(error_msg)
                raise Exception(error_msg)
            
            # Verificar se o PDF foi criado
            if not os.path.exists(output_pdf_path):
                # Listar arquivos criados para debug
                files_created = os.listdir(temp_dir)
                st.warning(f"⚠️ Arquivos gerados: {files_created}")
                
                # Procurar por PDFs com outros nomes
                pdf_files = [f for f in files_created if f.endswith(".pdf")]
                if pdf_files:
                    output_pdf_path = os.path.join(temp_dir, pdf_files[0])
                    st.write(f"✅ Usando arquivo PDF alternativo: {pdf_files[0]}")
                else:
                    raise Exception(
                        f"Arquivo PDF não foi gerado. Arquivos criados: {files_created}"
                    )

            # Ler PDF convertido
            with open(output_pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.success(f"✅ PDF gerado com sucesso! Tamanho: {len(pdf_bytes)} bytes")
                return pdf_bytes
                
        except subprocess.TimeoutExpired:
            st.error("⏱️ Conversão para PDF expirou (timeout após 60 segundos).")
            raise Exception("Conversão para PDF expirou (timeout).")
        except FileNotFoundError:
            st.error("❌ LibreOffice não encontrado no sistema.")
            raise Exception(
                "LibreOffice não encontrado no sistema. "
                "Por favor, instale LibreOffice: https://www.libreoffice.org/download/"
            )


def parse_signers(lines_text):
    signers = []
    invalid_lines = []

    for raw_line in lines_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if ";" not in line:
            invalid_lines.append(raw_line)
            continue

        name, email = [part.strip() for part in line.split(";", 1)]
        if not name or not email:
            invalid_lines.append(raw_line)
            continue

        signers.append({"name": name, "email": email, "action": "SIGN"})

    return signers, invalid_lines
