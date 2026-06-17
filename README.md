# NUVEM PESSOAL DE FOTOS E VÍDEOS

Sistema web Flask para guardar fotos e vídeos com login, upload, galeria, filtros por data e download/exclusão.

## Configuração local

1. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Gere um hash de senha:
   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha'))"
   ```
3. Copie `.env.example` para `.env` ou exporte as variáveis:
   ```bash
   export SECRET_KEY='uma-chave-secreta-grande'
   export NUVEM_USUARIO='bielpxt'
   export NUVEM_SENHA_HASH='hash-gerado-no-passo-anterior'
   export RECOVERY_CODE='15081998'
   ```
4. Opcionalmente configure Cloudinary também no ambiente local:
   ```bash
   export CLOUDINARY_CLOUD_NAME='seu-cloud-name'
   export CLOUDINARY_API_KEY='sua-api-key'
   export CLOUDINARY_API_SECRET='seu-api-secret'
   ```
5. Inicie:
   ```bash
   flask --app app run --host 0.0.0.0 --port 5000
   ```

Sem as variáveis do Cloudinary, os uploads são salvos em `uploads/` apenas para teste local. Em produção no Render Free, configure Cloudinary para que fotos e vídeos não dependam do filesystem efêmero do serviço.

## Armazenamento de fotos e vídeos

- Com Cloudinary configurado, fotos e vídeos são enviados para a pasta `nuvem_pessoal/` da conta Cloudinary.
- O banco (`nuvem.db`) salva apenas URLs seguras, `public_id`, tipo, tamanho, formato, usuário e data de upload.
- A galeria usa diretamente as URLs do Cloudinary para exibir fotos e vídeos.
- Ao excluir um item, o arquivo correspondente também é removido do Cloudinary quando as credenciais estiverem configuradas.
- Sem Cloudinary, a aplicação usa `uploads/fotos/` e `uploads/videos/` somente como fallback de desenvolvimento/teste.

## Rotas principais

- `/login`
- `/recuperar-senha`
- `/todas-as-fotos`
- `/fotos/hoje`
- `/fotos/ontem`
- `/fotos/data/10-06-2026`
- `/upload`
- `/pesquisar?data=10/06/2026`


## Recuperação de senha do administrador

A tela de login contém o link **ESQUECI MINHA SENHA**, que abre `/recuperar-senha`. Essa página pede o código de recuperação, a nova senha e a confirmação da nova senha.

- Configure o código pela variável de ambiente `RECOVERY_CODE`.
- A nova senha é salva apenas como hash seguro no banco da aplicação; a senha em texto puro não é armazenada.
- Se `RECOVERY_CODE` não estiver configurada, a aplicação usa temporariamente o fallback `15081998`. Configure a variável no Render para não depender desse fallback.

## Backup automático, exportação e importação

A aplicação mantém rotas de exportação/importação em ZIP para uso administrativo. No Render Free, o filesystem do serviço é efêmero; portanto, não use `uploads/`, `backups/` ou `/var/data` como armazenamento permanente. Guarde exportações fora do servidor e use Cloudinary para persistir as mídias.

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
- **BAIXAR BACKUP**: baixa o backup mais recente disponível no filesystem atual.

### Exportar nuvem

Use **EXPORTAR NUVEM** em `/configuracoes` para baixar um único arquivo ZIP contendo:

- arquivos locais de fallback em `uploads/`, se existirem;
- banco de dados `nuvem.db`, que contém URLs e metadados das mídias salvas no Cloudinary;
- manifesto em `metadata/manifest.json`.

Esse ZIP deve ser guardado fora do Render ou em outro provedor de armazenamento.

### Importar em outra instalação

1. Suba a aplicação em uma nova hospedagem.
2. Configure login e Cloudinary.
3. Entre em `/configuracoes`.
4. Em **IMPORTAR NUVEM**, envie o ZIP exportado.
5. A importação substitui `uploads/` e `nuvem.db` pelos dados do ZIP. Antes disso, a instalação atual gera um backup de segurança em `backups/antes-da-importacao-AAAAmmdd-HHMMSS.zip`.

> Importante: mantenha cópias dos ZIPs fora do servidor para proteção contra filesystem efêmero, exclusão acidental ou troca de hospedagem.

## Deploy no Render Free

Este repositório inclui um `render.yaml` para criar o serviço web no Render como Blueprint compatível com o plano gratuito.

Configurações principais do Blueprint:

- Runtime Python.
- Plano: `free`.
- Build command: `pip install -r requirements.txt`.
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`.
- Sem configuração `disk`, porque o Render Free não aceita disco persistente.
- Sem `DATA_DIR=/var/data`; não use `/var/data` como armazenamento permanente no plano gratuito.

### Passo a passo no Render

1. Crie uma conta Cloudinary e copie `cloud_name`, `api_key` e `api_secret` no painel da conta.
2. No Render, crie o serviço pelo Blueprint deste repositório.
3. Em **Environment**, configure:
   ```text
   CLOUDINARY_CLOUD_NAME=seu-cloud-name
   CLOUDINARY_API_KEY=sua-api-key
   CLOUDINARY_API_SECRET=seu-api-secret
   SECRET_KEY=uma-chave-secreta-grande
   NUVEM_USUARIO=bielpxt
   NUVEM_SENHA_HASH=hash-gerado-da-senha
   RECOVERY_CODE=15081998
   ```
4. Faça o deploy.
5. Para alterar ou confirmar o código de recuperação no Render, abra o serviço, vá em **Environment**, adicione ou edite `RECOVERY_CODE` com o valor desejado e clique em **Save Changes**. O Render fará um novo deploy/restart para aplicar a variável.
6. Acesse `/upload`, envie uma foto ou vídeo e confirme que a galeria abre a mídia por URL do Cloudinary.

### Configurar `RECOVERY_CODE` no Render

No painel do Render:

1. Entre no serviço `nuvem-pessoal`.
2. Abra **Environment**.
3. Adicione a variável `RECOVERY_CODE` com o código secreto escolhido.
4. Salve as alterações e aguarde o redeploy/restart.

Enquanto essa variável não existir no Render, a aplicação aceita temporariamente o fallback `15081998`.

Credenciais iniciais configuradas no Blueprint:

- Usuário: `bielpxt`
- Senha temporária: `Gabriel@2026`

> Recomendação: depois do primeiro acesso, gere uma nova senha, atualize `NUVEM_SENHA_HASH` no Render e faça redeploy.
