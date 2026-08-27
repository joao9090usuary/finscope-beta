# Política de segurança

## Versão suportada

A versão hospedada da Beta 5.2 recebe correções de segurança enquanto o período
de testes estiver ativo. Versões locais antigas devem ser atualizadas antes de
qualquer diagnóstico.

## Como relatar uma vulnerabilidade

Não publique tokens, dados financeiros, e-mails de participantes, capturas com
informações privadas ou detalhes exploráveis em uma issue pública.

Use a opção **Security > Report a vulnerability** do repositório para enviar um
relato privado. Inclua somente:

- descrição do comportamento observado;
- impacto provável;
- passos mínimos para reprodução com dados fictícios;
- versão ou commit testado;
- sugestão de correção, quando houver.

O relato será analisado antes de qualquer divulgação pública. Credenciais que
tenham sido expostas devem ser revogadas e substituídas nos serviços de origem;
apenas removê-las do commit mais recente não elimina o conteúdo do histórico.

## Boas práticas para contribuições

- Use exclusivamente dados e contas de teste.
- Mantenha `.env`, `secrets.toml`, chaves privadas e exportações fora do Git.
- Não reduza as validações de entrada, o isolamento por usuário ou as políticas
  RLS sem documentar a análise de risco.
- Execute os testes antes de abrir uma contribuição.
