# Checklist para a beta fechada do Revo

## Obrigatório antes de convidar usuários

- [ ] Hospedar a aplicação em um endereço HTTPS estável.
- [ ] Usar PostgreSQL persistente com backups automáticos.
- [ ] Definir `APP_ENV=production` e `APP_BASE_URL` com o endereço público.
- [ ] Configurar um provedor SMTP e testar a recuperação de senha, o spam e o remetente.
- [ ] Definir senhas diferentes para migração (`POSTGRES_PASSWORD`) e aplicação (`POSTGRES_APP_PASSWORD`).
- [ ] Manter `BETA_MAX_USERS=10` e definir um `BETA_INVITE_CODE` longo.
- [ ] Manter `BETA_ALLOWED_EMAILS` vazio para os convidados escolherem o próprio e-mail.
- [ ] Definir `STREAMLIT_SERVER_COOKIE_SECRET` com um valor aleatório longo.
- [ ] Criar o token da brapi.dev e definir `BRAPI_TOKEN`.
- [ ] Testar a Central de Ajuda e confirmar que ela não envia perguntas a serviços externos.
- [ ] Testar o bloqueio de tentativas repetidas de login.
- [ ] Criar uma política curta de privacidade e termos da beta.
- [ ] Informar que dados de mercado podem ter atraso e não são recomendação.
- [ ] Testar cadastro, login e recuperação de senha em celular e computador.
- [ ] Definir `FEEDBACK_TO_EMAIL` e confirmar o recebimento de um comentário.
- [ ] Testar exportação, importação e exclusão de uma conta de teste.
- [ ] Confirmar o health check `/_stcore/health` no provedor.
- [ ] Validar a restauração de pelo menos um backup do PostgreSQL.

## Durante a beta

- [ ] Conferir espaço, disponibilidade e logs diariamente.
- [ ] Conferir o consumo e os limites da API brapi.dev.
- [ ] Fazer backup do banco pelo menos uma vez ao dia.
- [ ] Revisar os comentários recebidos no e-mail privado e os logs do provedor.
- [ ] Não coletar CPF, dados bancários reais ou informações desnecessárias.
- [ ] Corrigir problemas críticos antes de ampliar o número de usuários.

## Encerramento

- [ ] Avisar a data de término aos participantes.
- [ ] Exportar ou excluir os dados conforme a política informada.
- [ ] Revogar credenciais SMTP temporárias e arquivar os backups com segurança.
