import io
from datetime import date
from docxtpl import DocxTemplate


def format_value(value):
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return value


def render_contract(template_bytes, context):
    template_stream = io.BytesIO(template_bytes)
    document = DocxTemplate(template_stream)

    normalized_context = {key: format_value(value) for key, value in context.items()}
    document.render(normalized_context)

    output = io.BytesIO()
    document.save(output)
    output.seek(0)
    return output


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
