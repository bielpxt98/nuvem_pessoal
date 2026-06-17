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


## Backup automático, exportação e importação

A aplicação continua usando o disco persistente local: os arquivos ficam em `uploads/` e o banco de dados em `nuvem.db`. Para evitar perda de fotos e vídeos caso o servidor seja apagado, a nuvem também cria backups em `backups/`.

### Backup automático diário

- Ao receber uma requisição, o sistema verifica a data do último backup.
- Se ainda não houver backup no dia atual, ele cria automaticamente um ZIP em `backups/backup-diario-AAAAmmdd-HHMMSS.zip`.
- O menu **Configurações** mostra o indicador **Último backup realizado**.

### Menu Configurações

Acesse `/configuracoes` após fazer login. O menu contém:

```text
CONFIGURAÇÕES
├── EXPORTAR NUVEM
├── IMPORTAR NUVEM
├── BACKUPS
```

Também há os botões:

- **FAZER BACKUP AGORA**: cria imediatamente um backup manual em `backups/backup-manual-AAAAmmdd-HHMMSS.zip`.
- **BAIXAR BACKUP**: baixa o backup mais recente.

### Exportar nuvem

Use **EXPORTAR NUVEM** em `/configuracoes` para baixar um único arquivo ZIP contendo:

- fotos de `uploads/fotos/`;
- vídeos de `uploads/videos/`;
- miniaturas/metadados auxiliares de `uploads/thumbs/`;
- banco de dados `nuvem.db`;
- manifesto em `metadata/manifest.json`.

Esse ZIP pode ser guardado fora do Render ou em outro provedor de armazenamento.

### Importar em outra instalação

1. Suba a aplicação em uma nova hospedagem.
2. Configure login e disco persistente normalmente.
3. Entre em `/configuracoes`.
4. Em **IMPORTAR NUVEM**, envie o ZIP exportado.
5. A importação substitui `uploads/` e `nuvem.db` pelos dados do ZIP. Antes disso, a instalação atual gera um backup de segurança em `backups/antes-da-importacao-AAAAmmdd-HHMMSS.zip`.

> Importante: mantenha cópias dos ZIPs fora do servidor para proteção contra exclusão do disco persistente ou troca de hospedagem.

## Deploy no Render

Este repositório inclui um `render.yaml` para criar o serviço web no Render como Blueprint.

Configurações principais do Blueprint:

- Runtime Python.
- Build command: `pip install -r requirements.txt`.
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`.
- Disco persistente montado em `/var/data` para manter `nuvem.db`, `uploads/` e `backups/` entre deploys.
- Variável `DATA_DIR=/var/data` para apontar a aplicação para o disco persistente.

Credenciais iniciais configuradas no Blueprint:

- Usuário: `admin`
- Senha: `ui1L7iN4V7o6w4gz`

> Recomendação: depois do primeiro acesso, gere uma nova senha, atualize `NUVEM_SENHA_HASH` no Render e faça redeploy.
