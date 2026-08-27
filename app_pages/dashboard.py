"""Dashboard financeira individual, configurável e exportável em PDF."""

from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from utils.database import (
    create_dashboard,
    delete_dashboard,
    get_dashboard,
    holdings_frame,
    transactions_frame,
    update_dashboard_period,
)
from utils.formatting import format_brl, format_percent
from utils.pdf_report import build_financial_report


PERIOD_LABELS = {
    1: "Último mês",
    3: "Últimos 3 meses",
    6: "Últimos 6 meses",
    12: "Último ano",
}
PERIOD_SHORT_LABELS = {1: "1 mês", 3: "3 meses", 6: "6 meses", 12: "1 ano"}
CHART_COLORS = [
    "#60A5FA",
    "#A78BFA",
    "#22D3EE",
    "#34D399",
    "#FBBF24",
    "#FB7185",
    "#818CF8",
    "#2DD4BF",
    "#F472B6",
]


def _dashboard_styles() -> None:
    """Aplica movimento sutil e acabamento responsivo somente nesta página."""
    st.html(
        """
        <style>
            [data-testid="stAppViewContainer"], [data-testid="stMain"] {
                overflow-x: clip;
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 92rem;
                padding-top: clamp(3.25rem, 6.5vh, 5rem) !important;
            }

            @keyframes dashboardFadeUp {
                from { opacity: 0; transform: translateY(14px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes dashboardGlow {
                0%, 100% { transform: translate3d(0, 0, 0) scale(1); opacity: .34; }
                50% { transform: translate3d(-1.5rem, .7rem, 0) scale(1.08); opacity: .5; }
            }

            .st-key-dashboard_hero,
            .st-key-dashboard_metrics,
            .st-key-dashboard_content,
            .st-key-dashboard_create_card {
                animation: dashboardFadeUp .55s cubic-bezier(.2,.75,.25,1) both;
            }

            .st-key-dashboard_metrics { animation-delay: .08s; }
            .st-key-dashboard_content { animation-delay: .15s; }

            .st-key-dashboard_hero,
            .st-key-dashboard_create_card {
                position: relative;
                isolation: isolate;
                overflow: hidden;
                border: 1px solid rgba(96, 165, 250, .24);
                border-radius: 1.4rem;
                background:
                    linear-gradient(125deg, rgba(37, 99, 235, .20), rgba(124, 58, 237, .11) 55%, rgba(15, 23, 42, .14)),
                    rgba(15, 23, 42, .46);
                box-shadow: 0 1rem 3rem rgba(2, 6, 23, .18);
            }

            .st-key-dashboard_hero {
                padding: clamp(1.3rem, 3vw, 2.3rem);
                margin-bottom: 1rem;
            }

            .st-key-dashboard_create_card {
                width: min(56rem, 100%);
                margin: clamp(2rem, 7vh, 5rem) auto 0;
                padding: clamp(1.5rem, 4vw, 3.25rem);
            }

            .st-key-dashboard_hero::after,
            .st-key-dashboard_create_card::after {
                content: "";
                position: absolute;
                z-index: -1;
                width: 18rem;
                height: 18rem;
                right: -5rem;
                top: -7rem;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(34, 211, 238, .42), transparent 66%);
                filter: blur(12px);
                animation: dashboardGlow 8s ease-in-out infinite;
                pointer-events: none;
            }

            .st-key-dashboard_hero h1,
            .st-key-dashboard_create_card h1 {
                letter-spacing: -.035em;
            }

            .st-key-dashboard_controls {
                position: sticky;
                top: 4.75rem;
                padding: 1.05rem;
                border: 1px solid rgba(148, 163, 184, .20);
                border-radius: 1.1rem;
                background: rgba(15, 23, 42, .42);
                box-shadow: 0 .8rem 2.3rem rgba(2, 6, 23, .12);
            }

            .st-key-dashboard_user_card {
                padding: .85rem;
                border-radius: .9rem;
                background: linear-gradient(135deg, rgba(59, 130, 246, .16), rgba(139, 92, 246, .10));
            }

            .st-key-dashboard_metrics [data-testid="stMetric"] {
                min-height: 8.7rem;
                border-color: rgba(148, 163, 184, .20) !important;
                border-radius: 1rem;
                background: linear-gradient(145deg, rgba(30, 41, 59, .52), rgba(15, 23, 42, .28));
                box-shadow: 0 .65rem 1.8rem rgba(2, 6, 23, .10);
            }

            .st-key-dashboard_chart,
            .st-key-dashboard_insights,
            .st-key-dashboard_recent,
            .st-key-dashboard_portfolio {
                border-color: rgba(148, 163, 184, .20) !important;
                border-radius: 1.1rem !important;
                background: rgba(15, 23, 42, .30);
            }

            @media (max-width: 900px) {
                [data-testid="stMainBlockContainer"] {
                    padding-inline: 1rem;
                    padding-top:
                        calc(4.1rem + env(safe-area-inset-top, 0px)) !important;
                }
                .st-key-dashboard_controls { position: static; }

                [data-testid="stHorizontalBlock"]:has(.st-key-dashboard_controls),
                .st-key-dashboard_hero [data-testid="stHorizontalBlock"],
                .st-key-dashboard_create_card [data-testid="stHorizontalBlock"],
                .st-key-dashboard_metrics [data-testid="stHorizontalBlock"],
                .st-key-dashboard_content [data-testid="stHorizontalBlock"] {
                    flex-direction: column !important;
                    align-items: stretch !important;
                }

                [data-testid="stHorizontalBlock"]:has(.st-key-dashboard_controls)
                    > [data-testid="stColumn"],
                .st-key-dashboard_hero [data-testid="stColumn"],
                .st-key-dashboard_create_card [data-testid="stColumn"],
                .st-key-dashboard_metrics [data-testid="stColumn"],
                .st-key-dashboard_content [data-testid="stColumn"] {
                    width: 100% !important;
                    min-width: 0 !important;
                    flex: 1 1 100% !important;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                .st-key-dashboard_hero,
                .st-key-dashboard_metrics,
                .st-key-dashboard_content,
                .st-key-dashboard_create_card,
                .st-key-dashboard_hero::after,
                .st-key-dashboard_create_card::after {
                    animation: none !important;
                }
            }
        </style>
        """
    )


def _start_date(months: int) -> date:
    """Calcula a data inicial inclusiva para o período selecionado."""
    return (pd.Timestamp(date.today()) - pd.DateOffset(months=months)).date()


def _monthly_flow(transactions: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Agrega receitas e despesas e preserva meses sem movimentação."""
    periods = pd.period_range(start=start, end=end, freq="M")
    if transactions.empty:
        pivot = pd.DataFrame(index=periods, data={"Receita": 0.0, "Despesa": 0.0})
    else:
        frame = transactions.copy()
        frame["Mês"] = pd.to_datetime(frame["Data"]).dt.to_period("M")
        pivot = frame.pivot_table(
            index="Mês",
            columns="Tipo",
            values="Valor",
            aggfunc="sum",
            fill_value=0,
        ).reindex(periods, fill_value=0)
        for kind in ("Receita", "Despesa"):
            if kind not in pivot:
                pivot[kind] = 0.0
    pivot = pivot.reset_index(names="Período")
    pivot["Mês"] = pivot["Período"].dt.to_timestamp()
    pivot["Saldo"] = pivot["Receita"] - pivot["Despesa"]
    return pivot


def _flow_chart(monthly: pd.DataFrame) -> alt.Chart:
    """Cria uma evolução em áreas suaves para receitas, despesas e saldo."""
    values = monthly.melt(
        id_vars=["Mês"],
        value_vars=["Receita", "Despesa", "Saldo"],
        var_name="Série",
        value_name="Valor",
    )
    base = alt.Chart(values).encode(
        x=alt.X(
            "yearmonth(Mês):O",
            title=None,
            axis=alt.Axis(format="%b/%y", labelAngle=0),
        ),
        y=alt.Y("Valor:Q", title="Valor (R$)", stack=None),
        color=alt.Color(
            "Série:N",
            scale=alt.Scale(
                domain=["Receita", "Despesa", "Saldo"],
                range=["#34D399", "#FB7185", "#60A5FA"],
            ),
            legend=alt.Legend(title=None, orient="top", direction="horizontal"),
        ),
        tooltip=[
            alt.Tooltip("yearmonth(Mês):O", title="Mês", format="%B/%Y"),
            alt.Tooltip("Série:N", title="Indicador"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f"),
        ],
    )
    area = base.mark_area(opacity=0.11, interpolate="monotone")
    line = base.mark_line(
        strokeWidth=3,
        interpolate="monotone",
        point=alt.OverlayMarkDef(size=42, filled=True),
    )
    return (
        alt.layer(area, line)
        .properties(height=320)
        .interactive(bind_y=False)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            gridColor="#334155",
            gridOpacity=0.28,
            labelColor="#CBD5E1",
            titleColor="#94A3B8",
        )
        .configure_legend(labelColor="#CBD5E1")
    )


def _donut_chart(expenses: pd.DataFrame) -> alt.Chart:
    """Cria uma rosca interativa das categorias de despesas."""
    grouped = (
        expenses.groupby("Categoria", as_index=False)["Valor"]
        .sum()
        .sort_values("Valor", ascending=False)
    )
    grouped["Participação"] = grouped["Valor"] / grouped["Valor"].sum()
    total = float(grouped["Valor"].sum())
    hover = alt.selection_point(
        fields=["Categoria"],
        on="pointerover",
        empty=True,
    )
    arc = (
        alt.Chart(grouped)
        .mark_arc(innerRadius=70, outerRadius=116, cornerRadius=5, padAngle=0.015)
        .encode(
            theta=alt.Theta("Valor:Q", stack=True),
            color=alt.Color(
                "Categoria:N",
                scale=alt.Scale(range=CHART_COLORS),
                legend=alt.Legend(title=None, orient="bottom", columns=2),
            ),
            opacity=alt.condition(hover, alt.value(1), alt.value(0.46)),
            tooltip=[
                alt.Tooltip("Categoria:N", title="Categoria"),
                alt.Tooltip("Valor:Q", title="Total", format=".2f"),
                alt.Tooltip("Participação:Q", title="Participação", format=".1%"),
            ],
        )
        .add_params(hover)
    )
    center = pd.DataFrame([{"Rótulo": "Total", "Total": format_brl(total)}])
    center_label = (
        alt.Chart(center)
        .mark_text(color="#94A3B8", fontSize=12, dy=-10)
        .encode(text="Rótulo:N")
    )
    center_value = (
        alt.Chart(center)
        .mark_text(color="#F1F5F9", fontSize=20, fontWeight=700, dy=13)
        .encode(text="Total:N")
    )
    return (
        alt.layer(arc, center_label, center_value)
        .properties(height=320)
        .configure_view(strokeOpacity=0)
        .configure_legend(labelColor="#CBD5E1")
    )


def _creation_screen(user: dict) -> None:
    """Apresenta a ativação consciente da dashboard para a conta."""
    with st.container(key="dashboard_create_card"):
        st.badge("Sua área personalizada", icon=":material/auto_awesome:", color="blue")
        st.title(f"Transforme seus registros em decisões, {user['name'].split()[0]}")
        st.write(
            "Crie uma visão particular das suas receitas, despesas e investimentos. "
            "A dashboard utilizará somente os dados da sua conta."
        )
        benefit_columns = st.columns(3)
        benefits = [
            (":material/donut_large:", "Gastos visíveis", "Entenda onde seu dinheiro está sendo usado."),
            (":material/date_range:", "Períodos flexíveis", "Compare 1, 3, 6 ou 12 meses de registros."),
            (":material/picture_as_pdf:", "Cópia em PDF", "Baixe um relatório organizado quando precisar."),
        ]
        for column, (icon, title, description) in zip(benefit_columns, benefits, strict=True):
            with column:
                with st.container(border=True):
                    st.subheader(f"{icon} {title}", anchor=False)
                    st.caption(description)

        default_label = st.segmented_control(
            "Período inicial",
            options=list(PERIOD_SHORT_LABELS.values()),
            default="1 mês",
            key="dashboard_creation_period",
        )
        selected_period = next(
            months for months, label in PERIOD_SHORT_LABELS.items() if label == default_label
        )
        if st.button(
            "Criar minha dashboard",
            type="primary",
            icon=":material/add_chart:",
            width="stretch",
        ):
            ok, message = create_dashboard(user["id"], selected_period)
            if ok:
                st.toast(message, icon=":material/check_circle:")
                st.rerun()
            st.error(message)

        st.caption(
            "Você poderá excluir esta dashboard quando quiser. Seus lançamentos e investimentos continuarão salvos."
        )


def _insight_text(income: float, expense: float, balance: float) -> tuple[str, str]:
    """Retorna uma leitura breve e educativa do período."""
    if income <= 0 and expense <= 0:
        return "Comece pelos registros", "Adicione receitas e despesas para liberar análises personalizadas."
    if income <= 0:
        return "Receita ainda não registrada", "Há despesas no período, mas nenhuma receita para comparação."
    ratio = expense / income
    if balance > 0 and ratio <= 0.7:
        return "Boa margem financeira", "As despesas consumiram até 70% das receitas registradas no período."
    if balance >= 0:
        return "Saldo positivo, margem apertada", "O período terminou positivo, mas há pouco espaço para imprevistos."
    return "Despesas acima das receitas", "Revise as categorias maiores e defina um limite para os próximos gastos."


def _dashboard_screen(user: dict, dashboard: dict) -> None:
    """Renderiza o painel completo e os controles de exportação/exclusão."""
    with st.container(key="dashboard_hero"):
        hero_text, hero_badge = st.columns([4, 1.2], vertical_alignment="center")
        with hero_text:
            st.title(f"Sua vida financeira em perspectiva, {user['name'].split()[0]}")
            st.write(
                "Acompanhe padrões, ajuste sua rota e leve um resumo organizado com você."
            )
        with hero_badge:
            st.badge("Dashboard particular", icon=":material/verified_user:", color="green")

    control_column, content_column = st.columns([0.88, 3.12], gap="large")

    with control_column:
        with st.container(key="dashboard_controls"):
            st.subheader("Painel de controle", anchor=False)
            with st.container(key="dashboard_user_card"):
                st.markdown(f"**:material/account_circle: {user['name']}**")
                st.caption(user["email"])

            period_options = list(PERIOD_LABELS.values())
            saved_period = dashboard["preferred_period"]
            selected_label = st.selectbox(
                "Período da análise",
                options=period_options,
                index=list(PERIOD_LABELS).index(saved_period),
                key="dashboard_period_select",
            )
            selected_period = next(
                months for months, label in PERIOD_LABELS.items() if label == selected_label
            )
            if selected_period != saved_period:
                update_dashboard_period(user["id"], selected_period)
                st.rerun()

            start = _start_date(selected_period)
            end = date.today()
            transactions = transactions_frame(user["id"], start_date=start)
            holdings = holdings_frame(user["id"])
            pdf_bytes = build_financial_report(
                user=user,
                months=selected_period,
                start_date=start,
                end_date=end,
                transactions=transactions,
                holdings=holdings,
            )

            st.caption(f"Período: {start:%d/%m/%Y} a {end:%d/%m/%Y}")
            st.download_button(
                "Baixar relatório em PDF",
                data=pdf_bytes,
                file_name=f"finscope-relatorio-{selected_period}m-{end:%Y-%m-%d}.pdf",
                mime="application/pdf",
                type="primary",
                icon=":material/download:",
                width="stretch",
                key="dashboard_pdf_download",
            )
            st.caption("O relatório é gerado somente para este download.")
            st.divider()

            @st.dialog("Excluir minha dashboard")
            def confirm_dashboard_deletion() -> None:
                st.warning(
                    "A organização desta dashboard será excluída. Suas receitas, despesas e posições de investimento não serão apagadas.",
                    icon=":material/warning:",
                )
                confirm, cancel = st.columns(2)
                with confirm:
                    if st.button(
                        "Excluir dashboard",
                        type="primary",
                        icon=":material/delete_forever:",
                        width="stretch",
                    ):
                        delete_dashboard(user["id"])
                        st.session_state.pop("dashboard_period_select", None)
                        st.rerun()
                with cancel:
                    if st.button("Cancelar", width="stretch"):
                        st.rerun()

            if st.button(
                "Excluir dashboard",
                icon=":material/delete_outline:",
                width="stretch",
                key="dashboard_delete_open",
            ):
                confirm_dashboard_deletion()

    with content_column:
        income = float(
            transactions.loc[transactions["Tipo"] == "Receita", "Valor"].sum()
        ) if not transactions.empty else 0.0
        expense = float(
            transactions.loc[transactions["Tipo"] == "Despesa", "Valor"].sum()
        ) if not transactions.empty else 0.0
        balance = income - expense
        savings_rate = (balance / income * 100) if income else 0.0
        portfolio_cost = (
            float((holdings["Quantidade"] * holdings["Preço médio"]).sum())
            if not holdings.empty
            else 0.0
        )
        monthly = _monthly_flow(transactions, start, end)

        with st.container(key="dashboard_metrics"):
            metric_columns = st.columns(4)
            metric_values = [
                ("Receitas", format_brl(income), monthly["Receita"].tolist(), ":material/trending_up:"),
                ("Despesas", format_brl(expense), monthly["Despesa"].tolist(), ":material/trending_down:"),
                ("Saldo do período", format_brl(balance), monthly["Saldo"].tolist(), ":material/account_balance:"),
                ("Custo do portfólio", format_brl(portfolio_cost), [], ":material/monitoring:"),
            ]
            for column, (label, value, chart_data, icon) in zip(metric_columns, metric_values, strict=True):
                with column:
                    chart_options = {}
                    if chart_data and any(abs(float(item)) > 0 for item in chart_data):
                        chart_options = {"chart_data": chart_data, "chart_type": "line"}
                    st.metric(
                        label,
                        value,
                        border=True,
                        label_visibility="visible",
                        **chart_options,
                    )
                    st.caption(icon)

        with st.container(key="dashboard_content"):
            trend_column, expense_column = st.columns([1.45, 1], gap="medium")
            with trend_column:
                with st.container(border=True, key="dashboard_chart"):
                    st.subheader("Fluxo financeiro", anchor=False)
                    st.caption("Receitas, despesas e saldo por mês.")
                    if transactions.empty:
                        st.info(
                            "Registre uma receita ou despesa para visualizar a evolução mensal.",
                            icon=":material/monitoring:",
                        )
                    else:
                        st.altair_chart(_flow_chart(monthly), width="stretch")

            with expense_column:
                with st.container(border=True, key="dashboard_insights"):
                    st.subheader("Despesas por categoria", anchor=False)
                    st.caption("Passe o cursor sobre o gráfico para ver os detalhes.")
                    expenses = (
                        transactions.loc[transactions["Tipo"] == "Despesa"]
                        if not transactions.empty
                        else transactions
                    )
                    if expenses.empty or float(expenses["Valor"].sum()) <= 0:
                        st.info(
                            "Registre uma despesa para visualizar a distribuição por categoria.",
                            icon=":material/donut_large:",
                        )
                    else:
                        st.altair_chart(_donut_chart(expenses), width="stretch")

            insight_title, insight_body = _insight_text(income, expense, balance)
            insight_column, portfolio_column = st.columns([1, 1], gap="medium")
            with insight_column:
                with st.container(border=True, key="dashboard_recent"):
                    st.subheader(f":material/lightbulb: {insight_title}", anchor=False)
                    st.write(insight_body)
                    if income > 0:
                        committed = min(expense / income, 1.0)
                        st.progress(
                            committed,
                            text=f"{format_percent(expense / income * 100, 0)} da receita comprometida",
                        )
                    st.metric("Taxa de economia", format_percent(savings_rate))

            with portfolio_column:
                with st.container(border=True, key="dashboard_portfolio"):
                    st.subheader(":material/account_balance: Portfólio virtual", anchor=False)
                    st.metric("Ativos acompanhados", str(len(holdings)))
                    st.write(f"Custo cadastrado: **{format_brl(portfolio_cost)}**")
                    st.caption(
                        "O custo cadastrado usa quantidade e preço médio, sem cotação on-line."
                    )

            with st.container(border=True):
                st.subheader("Movimentações recentes no período", anchor=False)
                if transactions.empty:
                    st.info(
                        "Ainda não há movimentações neste intervalo. Use **Finanças pessoais** para registrar seus dados.",
                        icon=":material/info:",
                    )
                else:
                    recent = transactions.head(8).drop(columns="id")
                    st.dataframe(
                        recent,
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                        },
                    )


_dashboard_styles()
current_user = st.session_state.user
dashboard_config = get_dashboard(current_user["id"])

if dashboard_config:
    _dashboard_screen(current_user, dashboard_config)
else:
    _creation_screen(current_user)

