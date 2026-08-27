# FinScope — Beta 5.2

Aplicação financeira desenvolvida em Python e Streamlit para controle de
finanças pessoais, análise técnica de ações da B3 e acompanhamento de um
portfólio virtual.

> **Status:** beta fechada para até 10 participantes. A Central de Ajuda utiliza
> respostas locais e não realiza chamadas a serviços de inteligência artificial.

## Código-fonte público e dados privados

O código-fonte pode ser consultado publicamente, mas a beta hospedada continua
limitada às contas autorizadas pela aplicação. Tornar o repositório público não
expõe o banco Neon, o serviço Render, a conta Brevo nem os dados das pessoas
usuárias: essas credenciais permanecem somente nas variáveis de ambiente dos
respectivos serviços.

- O arquivo `.env` nunca deve ser versionado; use apenas `.env.example` como
  referência.
- Não publique tokens, senhas, URLs de banco com credenciais, exportações de
  contas ou relatórios financeiros reais.
- Antes de enviar uma contribuição, confira `git diff --staged` e execute os
  testes do projeto.
- Falhas de segurança devem seguir as orientações de [SECURITY.md](SECURITY.md),
  sem exposição em uma issue pública.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Código-fonte público e dados privados](#código-fonte-público-e-dados-privados)
- [Tecnologias](#tecnologias)
- [Execução com Docker](#execução-com-docker)
- [Execução local](#execução-local)
- [Configuração](#configuração)
- [Testes](#testes)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Segurança e limitações](#segurança-e-limitações)
- [Documentação complementar](#documentação-complementar)

## Funcionalidades

- Cadastro e login com senhas protegidas por `bcrypt`.
- Limite de 10 contas e lista opcional de e-mails convidados.
- Recuperação de senha por link de uso único.
- Cadastro sem verificação obrigatória de e-mail na Beta 5.2.
- Separação dos dados por usuário.
- Registro e exclusão de receitas e despesas.
- Resumo de saldo, renda, gastos e taxa de economia.
- Dashboard individual com painel de controle para 1, 3, 6 ou 12 meses.
- Gráficos de fluxo financeiro e despesas por categoria em formato de rosca.
- Relatório financeiro em PDF gerado sob demanda e sem retenção no servidor.
- Criação e exclusão da dashboard sem apagar lançamentos ou investimentos.
- Consulta de cotações e histórico da B3 pela brapi.dev.
- Contingência identificada por meio do Yahoo Finance.
- Cálculo de MM20, MM50, RSI e MACD em Python.
- Portfólio virtual com patrimônio e resultado não realizado.
- Chat de ajuda local, com respostas revisadas sobre o uso da plataforma.
- Orçamentos mensais por categoria, metas financeiras e recorrências confirmáveis.
- Calendário com movimentações confirmadas e previsões mensais.
- Exportação integral da conta em ZIP e importação de lançamentos por CSV.
- Exclusão permanente da conta pela própria pessoa usuária.
- Caixa de comentários enviada diretamente ao e-mail privado do responsável.
- Resumo semanal opcional por e-mail e tarefa pronta para agendamento.
- Manifesto instalável para uso como aplicativo em navegadores compatíveis.
- Eventos mínimos de auditoria de login, sem armazenar senhas ou tokens.

## Tecnologias

| Camada | Tecnologia |
| --- | --- |
| Interface | Streamlit 1.62 ou superior |
| Linguagem | Python 3.13 |
| Persistência | PostgreSQL 17 ou SQLite para desenvolvimento |
| ORM | SQLAlchemy 2 |
| Visualização | Altair e gráficos nativos do Streamlit |
| Relatórios | ReportLab e PDF |
| Dados de mercado | brapi.dev e Yahoo Finance |
| Contêineres | Docker e Docker Compose |
| Testes | `unittest` |

## Execução com Docker

### 1. Criar o arquivo de configuração

No PowerShell, entre na pasta `FinScope-Beta-v5.1` e execute:

```powershell
Copy-Item .env.example .env
notepad .env
```

Defina senhas diferentes em `POSTGRES_PASSWORD` e `POSTGRES_APP_PASSWORD`, além
de um segredo longo em `STREAMLIT_SERVER_COOKIE_SECRET`. Para consultar todos
os ativos permitidos pelo seu plano, preencha também `BRAPI_TOKEN`.

### 2. Iniciar os serviços

```powershell
docker compose up --build -d
docker compose ps
```

Ao reutilizar um volume de uma versão anterior, o serviço
`database_password_sync` atualiza a credencial de migração e prepara o papel
restrito `finscope_app`. Em seguida, `database_migrate` aplica o esquema e a RLS
antes de liberar a aplicação. Nenhuma conta ou movimentação é apagada.

### 3. Abrir a aplicação

- Aplicação: `http://localhost:8501`
- Caixa de e-mails de desenvolvimento: `http://localhost:8025`

Para acompanhar os registros da aplicação:

```powershell
docker compose logs -f app
```

Se o banco não iniciar, consulte também o serviço de sincronização:

```powershell
docker compose logs --tail=50 database_password_sync database_migrate database app
```

Use `Ctrl+C` para sair da visualização dos registros sem encerrar os
contêineres.

## Execução local

O modo local utiliza SQLite quando `DATABASE_URL` não está definido.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Configuração

As configurações ficam no arquivo `.env`, que não deve ser enviado ao GitHub.

| Variável | Finalidade | Padrão |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | Senha do usuário do PostgreSQL | Obrigatória no Docker |
| `POSTGRES_APP_PASSWORD` | Senha exclusiva do papel restrito usado pelo site | Obrigatória no Docker |
| `BETA_MAX_USERS` | Quantidade máxima de participantes | `10` |
| `BETA_INVITE_CODE` | Código compartilhado para autorizar novos cadastros | Obrigatório em produção |
| `BETA_ALLOWED_EMAILS` | Lista de convidados separada por vírgulas | Vazia |
| `LOGIN_MAX_ATTEMPTS` | Tentativas antes do bloqueio temporário | `5` |
| `LOGIN_LOCK_MINUTES` | Duração do bloqueio, em minutos | `15` |
| `BRAPI_BASE_URL` | Endereço-base da API financeira | `https://brapi.dev/api` |
| `BRAPI_TOKEN` | Token privado da brapi.dev | Vazio |
| `APP_ENV` | Ambiente de execução | `development` |
| `APP_BASE_URL` | Endereço utilizado nos links de recuperação | `http://localhost:8501` |
| `APP_BIND_ADDRESS` | Interface de rede publicada pelo Docker | `127.0.0.1` |
| `STREAMLIT_SERVER_COOKIE_SECRET` | Assinatura estável dos cookies do Streamlit | Obrigatória |
| `EMAIL_PROVIDER` | Provedor de e-mail (`smtp` ou `brevo`) | `smtp` |
| `BREVO_API_KEY` | Chave secreta da API HTTPS usada no Render gratuito | Vazia |
| `SMTP_*` | Configuração SMTP usada no Docker local | Mailpit local |
| `FEEDBACK_TO_EMAIL` | Destino privado da caixa de comentários | Obrigatória |

Para manter a beta fechada sem definir antecipadamente os e-mails, gere um valor
aleatório longo em `BETA_INVITE_CODE` e compartilhe-o em particular com os
participantes. O limite de `BETA_MAX_USERS=10` continua sendo aplicado. Deixe
`BETA_ALLOWED_EMAILS` vazio para aceitar qualquer e-mail ou preencha a lista se
também quiser restringir endereços específicos. Em produção, a ausência do código
de convite bloqueia novos cadastros por segurança.

A Beta 5.2 não utiliza credenciais nem bibliotecas da OpenAI. O chat de ajuda
funciona inteiramente no servidor com respostas locais e auditáveis.

## Testes

Execute todos os testes a partir da raiz da versão:

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem autenticação, recuperação de senha, isolamento da dashboard,
planejamento, recorrências idempotentes, portabilidade, exclusão de conta,
exportação em PDF, formatação brasileira, leitura da brapi.dev e funcionamento
local da Central de Ajuda.

## Estrutura do projeto

```text
FinScope-Beta-v5.1/
├── app_pages/                 # Páginas da interface
├── jobs/                      # Tarefas agendáveis
├── static/                    # Manifesto e ícone instalável
├── tests/                     # Testes automatizados
├── utils/                     # Banco, APIs, PDF, e-mail e formatação
├── .streamlit/config.toml     # Tema visual
├── docker-compose.yml         # Aplicação, PostgreSQL e Mailpit
├── render.yaml                # Infraestrutura declarativa do Render
├── Dockerfile                 # Imagem segura da aplicação
├── streamlit_app.py           # Entrada, autenticação e navegação
└── requirements.txt           # Dependências Python
```

Os arquivos de interface contêm apenas apresentação e interação. As regras de
negócio e o acesso a serviços externos ficam em `utils/`, o que facilita testes
e manutenção.

## Segurança e limitações

- As senhas são armazenadas exclusivamente como hashes `bcrypt`.
- Todas as consultas usam a API parametrizada do SQLAlchemy.
- Registros financeiros são filtrados pelo identificador do usuário e protegidos
  novamente por RLS forçada no PostgreSQL.
- Cada conta possui no máximo uma dashboard; a exclusão remove apenas sua configuração.
- A confirmação de recorrências é idempotente e evita duplicidade por data.
- A aplicação conecta ao banco com o papel `finscope_app`, sem superusuário,
  `BYPASSRLS`, criação de banco ou criação de papéis.
- A caixa de comentários envia texto simples por SMTP ou pela API HTTPS da Brevo e não concede acesso global ao banco.
- A exclusão da conta remove os dados vinculados e exige confirmação explícita.
- Relatórios PDF são montados em memória no momento do download.
- O PostgreSQL não publica a porta `5432` no computador hospedeiro.
- O contêiner da aplicação utiliza usuário sem privilégios, sistema de arquivos
  somente leitura e remoção de capacidades Linux.
- A aplicação limita tentativas de login e quantidade de contas.
- Cotações podem apresentar atraso e dependem da fonte e do plano contratado.
- Dados de demonstração são identificados e não representam o mercado.
- O conteúdo é educacional e não constitui recomendação de investimento.

Nenhuma aplicação deve ser considerada “100% segura”. Antes da hospedagem,
conclua o checklist, configure HTTPS, teste a restauração dos backups e publique
uma política de privacidade adequada ao período da beta.

## Documentação complementar

- [Arquitetura e fluxo de dados](docs/ARCHITECTURE.md)
- [Guia de contribuição](CONTRIBUTING.md)
- [Histórico de alterações](CHANGELOG.md)
- [Checklist da beta](BETA-CHECKLIST.md)
- [Segurança e publicação](SEGURANCA-E-PUBLICACAO.md)
- [Publicação no Render](DEPLOY-RENDER.md)
