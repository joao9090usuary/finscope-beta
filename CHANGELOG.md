# Histórico de alterações

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.
O formato segue as categorias do Keep a Changelog.

## [Não publicado]

### Adicionado

- Código de convite configurável para manter a beta fechada sem predeterminar os e-mails.
- Bloqueio seguro de novos cadastros quando o convite não está configurado em produção.
- Dashboard individual com painel lateral e períodos de 1, 3, 6 ou 12 meses.
- Gráfico de rosca para distribuição de despesas por categoria.
- Relatório financeiro em PDF gerado sob demanda.
- Exclusão da dashboard sem remoção das finanças ou dos investimentos da conta.
- Orçamentos por categoria, metas, recorrências e calendário financeiro.
- Exportação da conta em ZIP, importação CSV e exclusão completa da conta.
- Caixa de comentários com envio direto ao e-mail privado do responsável.
- Resumo semanal opcional por e-mail e comando para execução agendada.
- Manifesto instalável, configuração de health check e Blueprint do Render.

### Alterado

- Navegação superior identifica quando a pessoa ainda precisa criar sua dashboard.
- Interface da nova área utiliza animações sutis com respeito à preferência de movimento reduzido.
- Central de Ajuda ampliada para explicar todas as áreas da Beta 5.2.

### Corrigido

- Remoção dos oito padrões apontados pela varredura SAST de 02/09/2026.
- Comandos administrativos do PostgreSQL deixaram de usar `sqlalchemy.text`;
  tabelas são resolvidas pelo metadado e papéis são citados com `psycopg.sql.Identifier`.
- Remoção do ponto de entrada legado que executava código dinamicamente com `exec`.
- Escape do relatório PDF migrado para `html.escape`, sem importação do parser XML padrão.
- Testes de regressão impedem a reintrodução dos padrões e validam a compilação da RLS.
- O serviço web não executa migrações e recusa papéis PostgreSQL com
  `SUPERUSER`/`BYPASSRLS` ou tabelas particulares sem RLS forçada.
- Provisionamento administrativo do Neon foi separado do processo web, sem
  imprimir ou persistir credenciais.
- GitHub Actions passou a executar testes, Bandit e auditoria de dependências;
  o Dependabot acompanha pacotes Python e as próprias Actions semanalmente.
- Isolamento no PostgreSQL com papel restrito, RLS forçada e contexto por transação.
- Exclusão de recorrências agora verifica o proprietário antes de tocar em dependências.
- Entradas textuais, exportação CSV e execução de HTML receberam proteções adicionais.
- Segredos permanecem apenas no ambiente, com credenciais distintas para migração e aplicação.
- Estabilidade da página de investimentos diante de tradutores e extensões do navegador.
- Validação de códigos de negociação da B3 antes da consulta de mercado.
- Revisão dos textos da autenticação e da página de investimentos em português brasileiro.

## [5.1.3] — 2026-08-23

### Corrigido

- Sincronização automática da senha ao reutilizar um volume PostgreSQL antigo.
- Tratamento amigável de indisponibilidade do banco, sem expor rastreamento técnico.

### Alterado

- Redesenho responsivo da tela de login e cadastro em um cartão dividido.
- Apresentação visual alinhada à identidade financeira do Revo.
- Redução dos espaçamentos e centralização do conteúdo de autenticação.
- Bloqueio do deslocamento e da rolagem horizontal em diferentes resoluções.

## [5.1.1] — 2026-08-23

### Alterado

- Centralização da tela de autenticação, sem rolagem da página.
- Revisão dos textos em português brasileiro.
- Formatação de valores monetários e percentuais no padrão brasileiro.
- Reorganização da documentação para leitura no GitHub.
- Validação adicional de dados financeiros no servidor.

### Removido

- Exigência de verificação de e-mail no cadastro e no login da Beta 5.1.
- Integração, dependência e chamadas à OpenAI na Beta 5.1.

### Adicionado

- Central de Ajuda em formato de chat, com respostas locais e auditáveis.
- Documentação de arquitetura e guia de contribuição.
- Testes do fluxo sem verificação de e-mail e do chat de ajuda local.

## [5.1.0] — 2026-08-22

### Adicionado

- Contas de usuário, recuperação de senha e limite da beta.
- Finanças pessoais, análise de ativos e portfólio virtual.
- PostgreSQL, Docker, Mailpit e integrações financeiras.
