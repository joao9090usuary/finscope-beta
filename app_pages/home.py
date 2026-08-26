"""Painel inicial com o resumo financeiro da conta autenticada."""

from datetime import date
from html import escape

import streamlit as st

from utils.database import holdings_frame, transactions_frame, user_summary
from utils.formatting import format_brl, format_percent


def _home_styles() -> None:
    """Aplica o acabamento glass da página inicial sem afetar outras telas."""
    st.html(
        """
        <style>
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                overflow-x: clip;
            }

            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 15% 0%, rgba(16, 185, 129, .11), transparent 29rem),
                    radial-gradient(circle at 92% 22%, rgba(59, 130, 246, .13), transparent 34rem),
                    var(--background-color);
            }

            [data-testid="stMainBlockContainer"] {
                width: min(100%, 92rem);
                padding-top: clamp(3.25rem, 6.5vh, 5rem) !important;
                padding-bottom: 3rem;
            }

            @keyframes homeGlassEnter {
                from { opacity: 0; transform: translateY(12px) scale(.992); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }

            @keyframes homeGlassGlow {
                0%, 100% { transform: translate3d(0, 0, 0) scale(1); opacity: .34; }
                50% { transform: translate3d(-1.2rem, .65rem, 0) scale(1.08); opacity: .52; }
            }

            .st-key-home_hero,
            .st-key-home_metrics,
            .st-key-home_quickstart,
            .st-key-home_recent,
            .st-key-home_month,
            .st-key-home_help {
                animation: homeGlassEnter .52s cubic-bezier(.2, .78, .25, 1) both;
            }

            .st-key-home_metrics { animation-delay: .06s; }
            .st-key-home_quickstart { animation-delay: .11s; }
            .st-key-home_recent,
            .st-key-home_month { animation-delay: .16s; }
            .st-key-home_help { animation-delay: .21s; }

            .st-key-home_hero,
            .st-key-home_quickstart,
            .st-key-home_recent,
            .st-key-home_month,
            .st-key-home_help,
            .st-key-home_metrics [data-testid="stMetric"] {
                border: 1px solid rgba(148, 163, 184, .20) !important;
                background:
                    linear-gradient(145deg, rgba(51, 65, 85, .58), rgba(15, 23, 42, .34)),
                    rgba(15, 23, 42, .36) !important;
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, .09),
                    0 .9rem 2.5rem rgba(2, 6, 23, .16);
                -webkit-backdrop-filter: blur(24px) saturate(145%);
                backdrop-filter: blur(24px) saturate(145%);
            }

            .st-key-home_hero {
                position: relative;
                isolation: isolate;
                min-height: 12.5rem;
                margin-bottom: 1rem;
                padding: clamp(1.4rem, 3.5vw, 2.5rem);
                overflow: hidden;
                border-radius: 1.55rem;
            }

            .st-key-home_hero::after {
                content: "";
                position: absolute;
                z-index: -1;
                width: 19rem;
                height: 19rem;
                right: -5rem;
                top: -8rem;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(52, 211, 153, .34), transparent 67%);
                filter: blur(11px);
                pointer-events: none;
                animation: homeGlassGlow 9s ease-in-out infinite;
            }

            .home-hero-copy {
                position: relative;
                z-index: 1;
                max-width: 48rem;
            }

            .home-kicker {
                display: inline-flex;
                align-items: center;
                margin-bottom: .65rem;
                padding: .34rem .68rem;
                border: 1px solid rgba(110, 231, 183, .22);
                border-radius: 999px;
                background: rgba(16, 185, 129, .09);
                color: #a7f3d0;
                font-size: .76rem;
                font-weight: 750;
                letter-spacing: .09em;
                text-transform: uppercase;
            }

            .home-greeting {
                margin: 0;
                color: #f8fafc;
                font-family: ui-rounded, "SF Pro Display", Inter, system-ui, sans-serif;
                font-size: clamp(2.65rem, 6vw, 5rem);
                font-weight: 780;
                line-height: .98;
                letter-spacing: -.055em;
            }

            .home-user-gradient {
                display: inline-block;
                padding-right: .08em;
                background: linear-gradient(105deg, #047857 0%, #10b981 48%, #86efac 100%);
                background-clip: text;
                -webkit-background-clip: text;
                color: transparent;
                -webkit-text-fill-color: transparent;
                filter: drop-shadow(0 .35rem 1.1rem rgba(16, 185, 129, .18));
            }

            .home-subtitle {
                max-width: 44rem;
                margin: .85rem 0 0;
                color: rgba(226, 232, 240, .78);
                font-size: clamp(.98rem, 1.7vw, 1.12rem);
                line-height: 1.65;
            }

            .st-key-home_metrics {
                margin-bottom: 1rem;
            }

            .st-key-home_metrics [data-testid="stMetric"] {
                position: relative;
                width: 100%;
                height: 10rem;
                min-height: 10rem;
                padding: 1.15rem 1.3rem 1.1rem !important;
                overflow: hidden;
                border-radius: 1.2rem;
                transition: transform .24s ease, border-color .24s ease, box-shadow .24s ease;
            }

            .st-key-home_metrics [data-testid="stColumn"] {
                display: flex;
                align-items: stretch;
            }

            .st-key-home_metrics [data-testid="stColumn"]
            > [data-testid="stVerticalBlock"] {
                width: 100%;
            }

            .st-key-home_metrics [data-testid="stMetric"]::before {
                content: "";
                position: absolute;
                inset: 0 auto auto 0;
                width: 72%;
                height: 1px;
                background: linear-gradient(90deg, rgba(255,255,255,.42), transparent);
                pointer-events: none;
            }

            .st-key-home_metrics [data-testid="stMetric"]:hover {
                transform: translateY(-3px);
                border-color: rgba(110, 231, 183, .30) !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.12),
                    0 1.2rem 2.8rem rgba(2, 6, 23, .22);
            }

            .st-key-home_metrics [data-testid="stMetricLabel"] {
                color: rgba(203, 213, 225, .76);
                font-weight: 650;
                margin-bottom: .3rem;
            }

            .st-key-home_metrics [data-testid="stMetricValue"] {
                letter-spacing: -.035em;
            }

            .st-key-home_quickstart,
            .st-key-home_recent,
            .st-key-home_month,
            .st-key-home_help {
                border-radius: 1.25rem !important;
            }

            .st-key-home_quickstart,
            .st-key-home_recent,
            .st-key-home_month {
                padding: clamp(1.15rem, 2.2vw, 1.55rem) !important;
            }

            .st-key-home_recent,
            .st-key-home_month {
                min-height: 22rem;
            }

            .st-key-home_quickstart > [data-testid="stVerticalBlock"],
            .st-key-home_recent > [data-testid="stVerticalBlock"],
            .st-key-home_month > [data-testid="stVerticalBlock"] {
                gap: .8rem;
            }

            .st-key-home_quickstart h2,
            .st-key-home_quickstart h3,
            .st-key-home_recent h2,
            .st-key-home_recent h3,
            .st-key-home_month h2,
            .st-key-home_month h3 {
                margin-top: 0;
                margin-bottom: .25rem;
            }

            .st-key-home_help [data-testid="stAlert"] {
                border: 0;
                border-radius: 1.15rem;
                background: rgba(37, 99, 235, .09);
            }

            @media (max-width: 880px) {
                [data-testid="stMainBlockContainer"] {
                    padding-inline: 1rem;
                    padding-top: 1.75rem !important;
                }

                .st-key-home_metrics [data-testid="stHorizontalBlock"] {
                    flex-direction: column !important;
                    align-items: stretch !important;
                }

                .st-key-home_metrics [data-testid="stColumn"] {
                    width: 100% !important;
                    min-width: 0 !important;
                    flex: 1 1 100% !important;
                }

                .st-key-home_metrics [data-testid="stMetric"] {
                    height: 8.7rem;
                    min-height: 8.7rem;
                }

                .st-key-home_recent,
                .st-key-home_month {
                    min-height: auto;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                .st-key-home_hero,
                .st-key-home_metrics,
                .st-key-home_quickstart,
                .st-key-home_recent,
                .st-key-home_month,
                .st-key-home_help,
                .st-key-home_hero::after,
                .st-key-home_metrics [data-testid="stMetric"] {
                    animation: none !important;
                    transition: none !important;
                }
            }
        </style>
        """
    )


user = st.session_state.user
summary = user_summary(user["id"])
transactions = transactions_frame(user["id"])
holdings = holdings_frame(user["id"])

_home_styles()
first_name = escape(str(user["name"]).split()[0])
with st.container(key="home_hero"):
    st.html(
        f"""
        <div class="home-hero-copy">
            <span class="home-kicker">Visão financeira</span>
            <h1 class="home-greeting">Olá, <span class="home-user-gradient">{first_name}</span></h1>
            <p class="home-subtitle">
                Esta é a visão geral da sua vida financeira no FinScope. Acompanhe
                seu saldo, seus hábitos e seus investimentos em um só lugar.
            </p>
        </div>
        """
    )

with st.container(key="home_metrics"):
    metric_columns = st.columns(4, gap="medium")
    with metric_columns[0]:
        balance_history = [summary["income"], summary["balance"]]
        balance_chart = (
            {"chart_data": balance_history}
            if any(abs(float(item)) > 0 for item in balance_history)
            else {}
        )
        st.metric(
            "Saldo registrado",
            format_brl(summary["balance"]),
            border=True,
            **balance_chart,
        )
    with metric_columns[1]:
        st.metric("Receitas", format_brl(summary["income"]), border=True)
    with metric_columns[2]:
        expense_ratio = (
            summary["expense"] / summary["income"] * 100 if summary["income"] else 0
        )
        st.metric(
            "Despesas",
            format_brl(summary["expense"]),
            border=True,
            delta=f"{format_percent(expense_ratio, 0)} da renda",
            delta_color="inverse",
        )
    with metric_columns[3]:
        st.metric("Ativos acompanhados", str(len(holdings)), border=True)

has_transactions = not transactions.empty
has_expense = (
    bool((transactions["Tipo"] == "Despesa").any()) if has_transactions else False
)
steps = [has_transactions, has_expense, not holdings.empty]

if not all(steps):
    with st.container(key="home_quickstart", border=True):
        st.subheader("Comece em poucos minutos", anchor=False)
        st.caption("Complete estes passos para obter uma visão financeira mais útil.")
        labels = [
            "Registre sua primeira receita",
            "Adicione uma despesa",
            "Cadastre um investimento",
        ]
        for done, label in zip(steps, labels, strict=True):
            icon = ":material/check_circle:" if done else ":material/radio_button_unchecked:"
            st.write(f"{icon} {label}")
        st.progress(
            sum(steps) / len(steps),
            text=f"{sum(steps)} de {len(steps)} passos concluídos",
        )

left, right = st.columns(2, gap="medium")
with left:
    with st.container(key="home_recent", border=True):
        st.subheader("Movimentações recentes", anchor=False)
        if transactions.empty:
            st.info(
                "Você ainda não registrou receitas ou despesas. Acesse "
                "**Finanças pessoais** para começar.",
                icon=":material/info:",
            )
        else:
            st.dataframe(
                transactions.head(6).drop(columns="id"),
                hide_index=True,
                column_config={
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                },
            )

with right:
    with st.container(key="home_month", border=True):
        st.subheader("Como está o seu mês?", anchor=False)
        if summary["income"] <= 0:
            st.caption("Registre uma receita para começar a calcular seu orçamento.")
        else:
            ratio = min(summary["expense"] / summary["income"], 1.0)
            st.progress(ratio, text=f"{format_percent(ratio * 100, 0)} da renda comprometida")
            if ratio <= 0.7:
                st.success(
                    "As despesas registradas estão abaixo de 70% da sua renda.",
                    icon=":material/check_circle:",
                )
            elif ratio <= 0.9:
                st.warning(
                    "Considere revisar seus gastos para preservar uma margem de segurança.",
                    icon=":material/warning:",
                )
            else:
                st.error(
                    "Suas despesas estão próximas ou acima da renda registrada.",
                    icon=":material/error:",
                )
        st.caption(f"Atualizado em {date.today():%d/%m/%Y}.")

with st.container(key="home_help"):
    st.info(
        "Precisa de orientação? Abra **Ajuda** no menu. O chat utiliza respostas "
        "locais e não envia dados a serviços de inteligência artificial.",
        icon=":material/help_center:",
    )
