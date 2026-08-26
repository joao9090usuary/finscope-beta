# Publicação da beta no Render

Este projeto inclui um `render.yaml` para criar o aplicativo gratuito no Render,
conectado a um PostgreSQL gratuito no Neon e à API HTTPS da Brevo. Nenhuma chave
é gravada no Git. A publicação exige contas do proprietário nos três serviços e
um repositório Git privado.

## 1. Antes da publicação

1. Envie esta pasta para um repositório **privado** no GitHub.
2. Confirme que `.env` não foi enviado; apenas `.env.example` deve existir no Git.
3. Crie o banco no Neon e copie a URL de conexão agrupada (`pooled`) com SSL.
4. No Render, selecione **New > Blueprint** e conecte o repositório.
5. Use `render.yaml` na raiz e revise os recursos antes de confirmar.

O Blueprint solicita os segredos abaixo:

- `APP_BASE_URL`: URL HTTPS exibida pelo Render, sem barra final;
- `DATABASE_URL`: URL agrupada e protegida por SSL fornecida pelo Neon;
- `BETA_INVITE_CODE`: código longo compartilhado somente com os dez convidados;
- `BRAPI_TOKEN`: token da brapi;
- `BREVO_API_KEY`: chave transacional privada criada na Brevo;
- `EMAIL_FROM`: remetente verificado na Brevo;
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
6. Aguarde 15 minutos sem acesso e valide também o primeiro carregamento após o repouso do plano gratuito.

## 3. Resumo semanal automático

O comando pronto é:

```bash
python jobs/send_weekly_summaries.py
```

O Cron Job do Render pode exigir plano pago. Na arquitetura gratuita, o botão de
teste continua disponível e o resumo automático fica reservado para uma etapa
posterior; recuperação de senha e comentários usam a API HTTPS normalmente.

## 4. Backup e restauração

- O Neon Free oferece uma janela limitada de restauração; faça também exportações
  periódicas com `pg_dump` antes de atualizações.
- Faça um backup manual imediatamente antes de cada atualização.
- Teste a restauração em um banco separado; backup nunca testado não é garantia.
- Não use `docker compose down -v` no computador local: `-v` apaga o volume.

## 5. Critério de abertura da beta

A beta pode ser compartilhada quando o health check estiver saudável, o fluxo de
recuperação de senha entregar e-mail real, o convite estiver ativo, o banco tiver
backup e o checklist `BETA-CHECKLIST.md` estiver integralmente validado.
