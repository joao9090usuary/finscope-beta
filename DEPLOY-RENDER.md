# Publicação da beta no Render

Este projeto inclui um `render.yaml` para criar o aplicativo e o PostgreSQL sem
gravar senhas no Git. A publicação exige uma conta do proprietário no Render e
um repositório Git privado; por isso, essa última autorização permanece manual.

## 1. Antes da publicação

1. Envie esta pasta para um repositório **privado** no GitHub.
2. Confirme que `.env` não foi enviado; apenas `.env.example` deve existir no Git.
3. No Render, selecione **New > Blueprint** e conecte o repositório.
4. Use `render.yaml` na raiz e revise os recursos antes de confirmar.

O Blueprint solicita os segredos abaixo:

- `APP_BASE_URL`: URL HTTPS exibida pelo Render, sem barra final;
- `BETA_INVITE_CODE`: código longo compartilhado somente com os dez convidados;
- `BRAPI_TOKEN`: token da brapi;
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` e `EMAIL_FROM`: dados do provedor de e-mail;
- `FEEDBACK_TO_EMAIL`: endereço privado que receberá os comentários;
- `STREAMLIT_SERVER_COOKIE_SECRET`: segredo aleatório com pelo menos 32 bytes.

O limite de dez contas é controlado no banco por `BETA_MAX_USERS=10`. A lista
`BETA_ALLOWED_EMAILS` permanece vazia, então cada participante escolhe livremente
seu próprio e-mail e sua própria senha, desde que possua o código de convite.

## 2. Verificações depois do primeiro deploy

1. Abra `https://SEU-ENDERECO.onrender.com/_stcore/health` e confirme `ok`.
2. Crie uma conta de teste com o convite.
3. Teste login, recuperação de senha, lançamento, dashboard, PDF e investimentos.
4. Em **Minha conta**, ative o resumo semanal e faça um envio de teste.
5. Envie um comentário pela barra lateral e confirme o recebimento no endereço configurado.

## 3. Resumo semanal automático

O comando pronto é:

```bash
python jobs/send_weekly_summaries.py
```

No Render, crie um **Cron Job** com o mesmo repositório e as mesmas variáveis do
serviço web. Uma agenda possível é `0 12 * * 1` (segunda-feira, 12:00 UTC). O cron
é opcional e pode exigir plano pago; até ele ser criado, o botão de teste continua
disponível para validar o SMTP.

## 4. Backup e restauração

- Ative os backups do PostgreSQL no painel do provedor antes de convidar usuários.
- Faça um backup manual imediatamente antes de cada atualização.
- Teste a restauração em um banco separado; backup nunca testado não é garantia.
- Não use `docker compose down -v` no computador local: `-v` apaga o volume.

## 5. Critério de abertura da beta

A beta pode ser compartilhada quando o health check estiver saudável, o fluxo de
recuperação de senha entregar e-mail real, o convite estiver ativo, o banco tiver
backup e o checklist `BETA-CHECKLIST.md` estiver integralmente validado.
