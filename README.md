# AGIL - Automação e Gestão Integrada Legal

Este repositório agora está organizado como um **sistema integrado modular** para centralizar automações de processos da CONSELT.

## Estrutura

```
app.py
pages/
	01_ATAs.py
	02_Contratos.py
modules/
	atas/
		page_atas.py
		config.py
		ia_utils.py
		authentique_utils.py
		email_utils.py
		history_utils.py
		data/
			email.json
			modelo_ata.docx
		examples/
			*.docx
	contratos/
		page_contratos.py
		config.py
		document_utils.py
		authentique_utils.py
		data/
			modelo_contrato_ps.docx
	ui/
		sidebar.py
```

## Módulos atuais

- `ATAs`: automação completa de geração, revisão, assinatura e notificação de atas.
- `Contratos`: preenchimento de contrato com template DOCX, conversão para PDF e envio para assinatura via Authentique.

## Como executar

1. Instale as dependências:
	 - `pip install -r requirements.txt`
2. Execute a interface inicial:
	 - `streamlit run app.py`
3. Na interface inicial, escolha o módulo `ATAs` ou `Contratos`.

## Próximos passos

- Adicionar novos módulos em `modules/<nome_do_modulo>/`.
- Conectar o menu da interface inicial aos novos módulos.
