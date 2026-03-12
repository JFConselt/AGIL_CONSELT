# Configuração do LibreOffice para Conversão de DOCX para PDF

O módulo de contratos agora usa **LibreOffice em modo headless** para converter documentos DOCX para PDF. Isso oferece melhor compatibilidade e não requer Microsoft Word instalado.

## Instalação

### Windows
1. Baixe o instalador do LibreOffice em: https://www.libreoffice.org/download/
2. Execute o instalador e conclua a instalação padrão
3. O aplicativo será instalado por padrão em:
   - `C:\Program Files\LibreOffice\program\soffice.exe` (64-bit)
   - `C:\Program Files (x86)\LibreOffice\program\soffice.exe` (32-bit)

**Opcional:** Para facilitar, adicione LibreOffice ao PATH do Windows:
- Nas Variáveis de Ambiente, adicione `C:\Program Files\LibreOffice\program` ao PATH

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install libreoffice
```

### Linux (Fedora/CentOS/RHEL)
```bash
sudo dnf install libreoffice
```

### macOS
```bash
brew install libreoffice
```

## Verificação da Instalação

Para verificar se LibreOffice está corretamente instalado, execute:

```bash
soffice --version
```

Ou no Windows, se não estiver no PATH:
```powershell
"C:\Program Files\LibreOffice\program\soffice.exe" --version
```

## Troubleshooting

### "LibreOffice não encontrado"
- Verifique se LibreOffice está instalado
- No Windows, adicione o caminho de instalação ao PATH do sistema
- Reinicie o terminal/aplicação após adicionar ao PATH

### Erro: "Falha ao converter DOCX para PDF"
- Verifique se há espaço em disco suficiente
- Tente converter o arquivo manualmente usando o LibreOffice
- Verifique permissões de pasta temporária

### Erro: conexão recusada ou timeout
- Libere porta 2002 (usada por LibreOffice em modo headless)
- Feche outras instâncias do LibreOffice
