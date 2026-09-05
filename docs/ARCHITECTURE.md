# Arquitetura do Revo

## Visão geral

O Revo utiliza uma arquitetura modular adequada a uma beta pequena. O
Streamlit controla a interface e a sessão autenticada; o SQLAlchemy concentra a
persistência; e os módulos de serviço encapsulam integrações externas.

```text
Navegador
   │
   ▼
Streamlit ──► páginas da aplicação
   │                 │
   │                 ├──► utils.database ──► PostgreSQL ou SQLite
   │                 ├──► utils.finance  ──► brapi.dev / Yahoo Finance
   │                 ├──► utils.pdf_report ──► PDF em memória
   │                 └──► utils.email_service ──► SMTP / Mailpit
   │
   └──► sessão temporária do usuário
```

## Componentes

### Entrada e autenticação

`streamlit_app.py` configura a página, inicializa o banco, controla login,
cadastro e recuperação de senha, além de construir a navegação superior.

Na Beta 5.2, o cadastro não exige confirmação de e-mail. A coluna legada e as
funções de verificação permanecem isoladas para eventual reativação em uma
versão futura.

### Páginas

- `app_pages/home.py`: apresenta indicadores e primeiros passos.
- `app_pages/dashboard.py`: cria a visão individual, controla o período e
  disponibiliza o relatório financeiro em PDF.
- `app_pages/personal_finance.py`: administra receitas e despesas.
- `app_pages/investments.py`: consulta ativos, calcula indicadores e mantém o
  portfólio virtual.
- `app_pages/assistant.py`: apresenta o chat local da Central de Ajuda.
- `app_pages/planning.py`: concentra orçamentos, metas, recorrências e calendário.
- `app_pages/settings.py`: preferências, portabilidade e exclusão da conta.

### Persistência

`utils/database.py` define os modelos e as operações de negócio. Toda alteração
que pertence a uma conta recebe o `user_id` autenticado, e exclusões validam o
proprietário na própria consulta. No PostgreSQL, uma segunda camada usa RLS
forçada com contexto definido por transação; consultas sem contexto não enxergam
linhas particulares.

### Relatórios

`utils/pdf_report.py` monta o relatório com ReportLab no momento do download.
O arquivo permanece em memória e inclui somente as movimentações do período e
as posições pertencentes à conta autenticada.

### Dados de mercado

`utils/finance.py` tenta consultar a brapi.dev. Em caso de indisponibilidade,
utiliza o Yahoo Finance como contingência. Se ambas as fontes falharem, produz
dados locais claramente identificados como demonstração.

### Portabilidade

`utils/data_portability.py` exporta os dados da própria conta em memória e
valida importações CSV linha a linha, reutilizando as regras do domínio.

### E-mail

`utils/email_service.py` utiliza SMTP real em produção e Mailpit durante o
desenvolvimento. A recuperação de senha emprega tokens aleatórios, armazenados
somente como hash, com validade de 30 minutos e uso único. Resumos semanais
dependem de consentimento explícito e contêm apenas valores agregados. A caixa de
comentários envia texto simples diretamente ao endereço privado configurado.

### Central de Ajuda

`utils/help_assistant.py` seleciona respostas locais por palavras-chave. O
mecanismo é determinístico, auditável e não utiliza APIs, modelos de IA nem
dados financeiros da conta.

## Modelo de dados

| Entidade | Responsabilidade |
| --- | --- |
| `User` | Identidade e credencial protegida da conta |
| `AuthToken` | Recuperação de senha e recursos futuros de verificação |
| `LoginThrottle` | Bloqueio temporário de tentativas repetidas |
| `Transaction` | Receitas e despesas vinculadas ao usuário |
| `Holding` | Posições do portfólio virtual |
| `Dashboard` | Preferência individual de período e estado de criação |
| `Budget` | Limite mensal por categoria |
| `SavingsGoal` | Objetivo e progresso financeiro |
| `RecurringEntry` | Previsão mensal configurada pela pessoa usuária |
| `RecurringOccurrence` | Confirmação idempotente da previsão |
| `Feedback` | Relatos históricos pertencentes à própria conta |
| `UserPreference` | Consentimentos de comunicação |
| `SecurityEvent` | Auditoria mínima de autenticação |

## Decisões de segurança

- Segredos são lidos de variáveis de ambiente.
- A senha nunca é registrada nem armazenada em texto simples.
- Entradas relevantes são validadas novamente no servidor.
- O papel usado pelo site não é superusuário, não possui `BYPASSRLS` e não cria papéis.
- Tabelas particulares usam RLS forçada e contexto de usuário local à transação.
- Mensagens de autenticação evitam revelar a existência de uma conta.
- Erros inesperados das APIs não são exibidos integralmente ao usuário.
- O banco permanece em uma rede interna do Docker.
- A exclusão da dashboard não remove movimentações nem investimentos.
- O PDF não é persistido no servidor após a resposta de download.

## Evolução prevista

Antes de uma beta pública, recomenda-se adicionar migrações versionadas,
observabilidade centralizada, testes de carga, proteção por proxy reverso HTTPS,
backup automatizado com restauração validada e revisão independente de
segurança e privacidade.
