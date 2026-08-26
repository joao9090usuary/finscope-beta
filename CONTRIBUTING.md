# Como contribuir

## Preparação

1. Crie um ambiente virtual.
2. Instale `requirements.txt`.
3. Copie `.env.example` para `.env` e use somente credenciais de teste.
4. Execute os testes antes de alterar o código.

## Padrão de código

- Siga a PEP 8 e utilize nomes descritivos.
- Escreva docstrings em módulos, classes e funções públicas.
- Mantenha textos da interface em português brasileiro formal e claro.
- Preserve a separação entre interface (`app_pages/`) e regras de negócio
  (`utils/`).
- Nunca inclua senhas, tokens, bancos locais ou arquivos `.env` no Git.
- Valide no servidor qualquer dado que afete segurança, autorização ou banco.

## Commits e solicitações de alteração

Use mensagens objetivas no modo imperativo, por exemplo:

```text
Corrige validação de lançamentos financeiros
```

Uma solicitação de alteração deve informar:

- problema ou necessidade;
- solução adotada;
- impacto visual ou de dados;
- testes executados;
- instruções de migração, quando necessárias.

## Verificação

```powershell
python -m compileall -q .
python -m unittest discover -s tests -v
```

Mudanças na interface também devem ser verificadas em computador e celular.
