# NUVEM PESSOAL DE FOTOS E VÍDEOS

Sistema web Flask para guardar fotos e vídeos com login, upload, galeria, filtros por data e download/exclusão.

## Configuração

1. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Gere um hash de senha:
   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha'))"
   ```
3. Configure variáveis de ambiente:
   ```bash
   export SECRET_KEY='uma-chave-secreta-grande'
   export NUVEM_USUARIO='admin'
   export NUVEM_SENHA_HASH='hash-gerado-no-passo-anterior'
   ```
4. Inicie:
   ```bash
   flask --app app run --host 0.0.0.0 --port 5000
   ```

## Rotas principais

- `/login`
- `/todas-as-fotos`
- `/fotos/hoje`
- `/fotos/ontem`
- `/fotos/data/10-06-2026`
- `/upload`
- `/pesquisar?data=10/06/2026`

Os arquivos enviados ficam em `uploads/fotos/` ou `uploads/videos/`, e os metadados ficam em `nuvem.db`.
