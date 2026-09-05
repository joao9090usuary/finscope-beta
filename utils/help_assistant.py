"""Respostas locais da Central de Ajuda do Revo.

O módulo não utiliza inteligência artificial, serviços externos ou dados
financeiros da conta. A resposta é escolhida por regras simples e auditáveis.
"""

from __future__ import annotations

import re
import unicodedata


HELP_TOPICS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"cadastro", "cadastrar", "conta", "inscrever"}),
        "Para criar sua conta, saia da sessão atual e selecione **Criar conta** "
        "na tela inicial. Informe nome, e-mail e uma senha com pelo menos 10 "
        "caracteres, incluindo letra maiúscula, letra minúscula e número, além "
        "do código de convite. Nesta beta, não é necessário confirmar o e-mail.",
    ),
    (
        frozenset({"login", "entrar", "acesso", "senha"}),
        "Na tela inicial, selecione **Entrar**, informe seu e-mail e sua senha e "
        "pressione **Entrar**. Após cinco tentativas incorretas, o acesso fica "
        "temporariamente bloqueado por 15 minutos.",
    ),
    (
        frozenset({"esqueci", "recuperar", "redefinir", "trocar"}),
        "Na tela de login, selecione **Esqueceu sua senha?**. Informe o e-mail "
        "da conta e abra o link recebido. O link expira em 30 minutos e pode ser "
        "utilizado uma única vez.",
    ),
    (
        frozenset(
            {
                "gasto",
                "gastos",
                "despesa",
                "despesas",
                "receita",
                "receitas",
                "lancamento",
            }
        ),
        "Acesse **Finanças pessoais** e selecione **Novo lançamento**. Escolha "
        "Receita ou Despesa, preencha categoria, valor, data e descrição e, por "
        "fim, selecione **Salvar lançamento**.",
    ),
    (
        frozenset({"excluir", "apagar", "remover", "lancamento"}),
        "Em **Finanças pessoais**, abra **Excluir um lançamento**, escolha o "
        "registro desejado e confirme a exclusão. Essa ação remove somente dados "
        "da sua própria conta.",
    ),
    (
        frozenset({"saldo", "economia", "renda", "resumo"}),
        "O saldo registrado corresponde às receitas menos as despesas. A taxa de "
        "economia representa a parcela da renda que permaneceu como saldo. Os "
        "valores dependem dos lançamentos cadastrados por você.",
    ),
    (
        frozenset({"orcamento", "limite", "categoria", "planejamento"}),
        "Acesse **Planejamento > Orçamentos** para definir um limite mensal por "
        "categoria. O Revo compara esse valor com as despesas do mês e avisa "
        "quando o limite é excedido.",
    ),
    (
        frozenset({"meta", "objetivo", "reserva", "guardar"}),
        "Em **Planejamento > Metas**, informe o objetivo, o valor-alvo e o que já "
        "foi guardado. Você pode atualizar o total a qualquer momento e acompanhar "
        "o progresso visualmente.",
    ),
    (
        frozenset({"recorrente", "recorrencia", "salario", "aluguel", "mensal"}),
        "Use **Planejamento > Recorrências** para cadastrar salário, aluguel ou "
        "outro compromisso mensal. A previsão só altera seu saldo depois que você "
        "a confirma no mês correspondente.",
    ),
    (
        frozenset({"calendario", "previsto", "vencimento", "agenda"}),
        "O **Calendário**, dentro de Planejamento, reúne lançamentos confirmados e "
        "previsões recorrentes do mês. Itens previstos não alteram o saldo.",
    ),
    (
        frozenset({"exportar", "baixar", "copia", "csv", "importar"}),
        "Em **Minha conta > Meus dados**, baixe uma cópia em ZIP ou importe "
        "lançamentos por CSV. A exportação não contém senha, convite ou tokens.",
    ),
    (
        frozenset({"excluir", "conta", "privacidade", "permanente"}),
        "Em **Minha conta > Privacidade**, você pode excluir permanentemente sua "
        "conta e todos os dados vinculados. Leia o aviso e digite a frase de "
        "confirmação; essa ação não pode ser desfeita.",
    ),
    (
        frozenset({"feedback", "sugestao", "erro", "avaliar"}),
        "Selecione **Enviar feedback** na barra lateral e escreva seu comentário. "
        "A mensagem será encaminhada por e-mail diretamente "
        "ao responsável pela beta.",
    ),
    (
        frozenset({"instalar", "celular", "atalho", "pwa"}),
        "Em uma hospedagem HTTPS, abra **Minha conta > Instalar** e use a opção "
        "**Instalar aplicativo** ou **Adicionar à tela inicial** do navegador.",
    ),
    (
        frozenset(
            {"investimento", "investimentos", "ativo", "acao", "ticker", "b3"}
        ),
        "Acesse **Investimentos**, informe o código de negociação do ativo, como "
        "PETR4, escolha o período e selecione **Analisar**. Para acompanhar uma "
        "posição, use **Adicionar este ativo ao meu portfólio**.",
    ),
    (
        frozenset({"portfolio", "carteira", "posicao", "quantidade", "patrimonio"}),
        "O portfólio é uma simulação. Informe a quantidade e o preço médio pago "
        "para calcular o patrimônio estimado e o resultado não realizado. Nenhuma "
        "operação real de compra ou venda é executada.",
    ),
    (
        frozenset({"rsi", "sobrecompra", "sobrevenda"}),
        "O RSI mede a intensidade das variações recentes. Valores abaixo de 30 "
        "podem indicar sobrevenda, e valores acima de 70 podem indicar "
        "sobrecompra. É um indicador histórico, não uma garantia de resultado.",
    ),
    (
        frozenset({"macd", "sinal", "tendencia"}),
        "O MACD compara médias móveis exponenciais para auxiliar na identificação "
        "de mudanças de tendência. O cruzamento com a linha de sinal é apenas um "
        "dado histórico e não constitui recomendação de investimento.",
    ),
    (
        frozenset({"mm20", "mm50", "media", "medias"}),
        "A MM20 representa a média dos últimos 20 pregões, e a MM50, a média dos "
        "últimos 50. Elas ajudam a visualizar tendências, mas não preveem o "
        "comportamento futuro do ativo.",
    ),
    (
        frozenset({"cotacao", "preco", "atraso", "fonte", "brapi", "yahoo"}),
        "A fonte principal é a brapi.dev, com Yahoo Finance como contingência. A "
        "frequência e o atraso das cotações dependem da fonte e do plano "
        "contratado. Dados de demonstração são identificados na tela.",
    ),
    (
        frozenset({"seguranca", "privacidade", "dados", "bcrypt"}),
        "As senhas são protegidas com bcrypt, e os registros são separados por "
        "conta. Este chat funciona localmente por regras e não envia suas "
        "perguntas, e-mails ou dados financeiros a serviços de IA.",
    ),
)

FALLBACK_RESPONSE = (
    "Posso ajudar com **cadastro**, **login**, **recuperação de senha**, "
    "**receitas e despesas**, **saldo**, **portfólio**, **cotações**, **RSI**, "
    "**orçamentos**, **metas**, **recorrências**, **calendário**, **exportação**, "
    "**feedback**, **MACD**, **médias móveis** e **privacidade**. Reformule sua dúvida usando "
    "um desses assuntos."
)


def _normalize(text: str) -> set[str]:
    """Normaliza acentos e pontuação para comparar as palavras da pergunta."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def answer_help_question(question: str) -> str:
    """Retorna a resposta local mais relacionada à pergunta informada."""
    words = _normalize(question)
    if not words:
        return FALLBACK_RESPONSE

    greeting_words = {"oi", "ola", "bom", "boa", "dia", "tarde", "noite"}
    if words.issubset(greeting_words):
        return (
            "Olá! Sou a Central de Ajuda do Revo. "
            + FALLBACK_RESPONSE
        )

    best_score = 0
    best_response = FALLBACK_RESPONSE
    for keywords, response in HELP_TOPICS:
        score = len(words & keywords)
        if score > best_score:
            best_score = score
            best_response = response
    return best_response
