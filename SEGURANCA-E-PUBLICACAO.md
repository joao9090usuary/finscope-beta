# Segurança e publicação do Revo

## Fase 1 — beta fechada para 10 pessoas

1. Copie `.env.example` para `.env` e nunca envie esse arquivo a outra pessoa.
2. Mantenha `BETA_MAX_USERS=10`, gere um valor aleatório longo em
   `BETA_INVITE_CODE` e compartilhe-o apenas com os participantes. Deixe
   `BETA_ALLOWED_EMAILS` vazio para que cada pessoa escolha o próprio e-mail ou
   preencha-o somente se também quiser limitar endereços específicos.
3. Use senhas longas e diferentes em `POSTGRES_PASSWORD` e
   `POSTGRES_APP_PASSWORD`. A primeira é exclusiva para migrações; a aplicação
   recebe apenas a segunda, associada a um papel sem privilégios elevados.
4. Crie um token no painel da brapi.dev, defina um limite de uso no provedor e nunca
   coloque essa credencial no código. A Central de Ajuda é local e não exige chave de IA.
5. Configure SMTP real para recuperação de senha e comentários, defina
   `FEEDBACK_TO_EMAIL`, `APP_ENV=production` e
   `APP_BASE_URL=https://...`. O Mailpit serve somente para desenvolvimento e está
   acessível apenas no próprio computador ou servidor.
6. Publique o Streamlit atrás de um proxy HTTPS, mantendo `APP_BIND_ADDRESS=127.0.0.1`.
   Assim, o proxy é a única entrada pública para o contêiner.
7. Faça backup diário do PostgreSQL e execute ao menos uma restauração de teste antes de
   receber dados de participantes.
8. Ative logs, monitoramento de disponibilidade e alertas de erro. Informe aos participantes
   o período da beta, a finalidade educacional e como pedir exclusão dos dados.

### Se o volume PostgreSQL já existe com a senha local

Não apague o volume. A composição atual sincroniza automaticamente a senha
gravada no PostgreSQL, cria o papel restrito `revo_app` e aplica RLS antes
de iniciar o aplicativo:

```powershell
docker compose up --build -d
docker compose logs --tail=50 database_password_sync database_migrate app
```

O serviço `database_password_sync` conecta-se apenas pelo soquete interno do
PostgreSQL, não possui acesso à rede e termina antes de o Streamlit iniciar. Os
dados persistidos no volume são preservados.

As tabelas particulares usam `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL
SECURITY`. Cada transação recebe `revo.user_id` no servidor; sem esse contexto,
o PostgreSQL nega a leitura e a alteração das linhas.

Se a sincronização automática não terminar com o código `0`, use o procedimento
interativo de contingência:

```powershell
docker compose exec database psql -U revo -d revo
```

No prompt do PostgreSQL, execute `\password revo`, informe a mesma senha do
`.env`, saia com `\q` e execute novamente `docker compose up -d`.

## Critérios para abrir ao público

Antes de remover a lista de convidados ou aumentar o limite:

- Migre para PostgreSQL gerenciado com criptografia, backups automáticos e restauração
  testada; não publique a porta 5432.
- Use um gerenciador de segredos da nuvem e estabeleça rotação das credenciais da
  brapi.dev, do SMTP e do banco.
- Adicione observabilidade, alertas, rastreamento de erros e uma página de status.
- Faça testes de carga, segurança de dependências e revisão independente dos fluxos de
  autenticação, autorização e exclusão de dados.
- Defina termos, política de privacidade, retenção/exportação de dados e canal de suporte.
- Substitua os limites locais por rate limiting centralizado se houver mais de uma instância
  da aplicação.
- Separe ambientes de desenvolvimento, homologação e produção e automatize as migrações.

A versão atual é apropriada para uma beta pequena depois que os itens da primeira fase
forem realmente configurados. Ela ainda não deve ser aberta ao público sem cumprir os
critérios acima.

## Recursos reservados para versões futuras

A verificação de e-mail permanece isolada no código, mas está desativada na experiência
da Beta 5.1. A Central de Ajuda utiliza somente respostas locais. Uma eventual integração
com IA exigirá novos testes de segurança, privacidade, qualidade e controle de custos.
