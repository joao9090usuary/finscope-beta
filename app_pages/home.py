"""Visão geral financeira da conta autenticada."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from utils.database import holdings_frame, transactions_frame, user_summary
from utils.formatting import format_brl, format_percent
from utils.ui import chart_theme, empty_chart_state, metric_card_grid, page_header


FLOW_COLORS = ["#34D399", "#FF6B5F", "#665CFF"]
CATEGORY_COLORS = ["#5B8FF9", "#34D399", "#39C4DF", "#FBBF24", "#FF8B4C", "#FF6B5F", "#94A3B8"]
MONTH_NAMES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _monthly_flow(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        return pd.DataFrame(columns=["Mês", "Receita", "Despesa", "Saldo acumulado"])
    frame = transactions.copy()
    frame["Mês"] = pd.to_datetime(frame["Data"]).dt.to_period("M").dt.to_timestamp()
    pivot = frame.pivot_table(index="Mês", columns="Tipo", values="Valor", aggfunc="sum", fill_value=0)
    for kind in ("Receita", "Despesa"):
        if kind not in pivot:
            pivot[kind] = 0.0
    pivot = pivot.reset_index().sort_values("Mês").tail(12)
    pivot["Saldo acumulado"] = (pivot["Receita"] - pivot["Despesa"]).cumsum()
    return pivot


def _flow_chart(monthly: pd.DataFrame) -> alt.Chart:
    theme = chart_theme()
    values = monthly.melt(
        id_vars=["Mês"],
        value_vars=["Receita", "Despesa", "Saldo acumulado"],
        var_name="Série",
        value_name="Valor",
    )
    base = alt.Chart(values).encode(
        x=alt.X("yearmonth(Mês):T", title=None, axis=alt.Axis(format="%b/%y", labelAngle=0)),
        y=alt.Y("Valor:Q", title=None),
        color=alt.Color(
            "Série:N",
            scale=alt.Scale(domain=["Receita", "Despesa", "Saldo acumulado"], range=FLOW_COLORS),
            legend=alt.Legend(title=None, orient="top", direction="horizontal"),
        ),
        tooltip=[
            alt.Tooltip("yearmonth(Mês):T", title="Mês", format="%B/%Y"),
            alt.Tooltip("Série:N", title="Indicador"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f"),
        ],
    )
    area = base.mark_area(opacity=.12, interpolate="monotone")
    line = base.mark_line(strokeWidth=2.5, interpolate="monotone", point=alt.OverlayMarkDef(size=34, filled=True))
    return (
        alt.layer(area, line)
        .properties(height=275)
        .interactive(bind_y=False)
        .configure(background=theme["surface"])
        .configure_view(strokeOpacity=0)
        .configure_axis(gridColor=theme["grid"], gridOpacity=.45, labelColor=theme["muted"], titleColor=theme["muted"])
        .configure_legend(labelColor=theme["muted"], symbolSize=90)
    )


def _donut_chart(expenses: pd.DataFrame) -> alt.Chart:
    theme = chart_theme()
    grouped = expenses.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False).head(7)
    grouped["Participação"] = grouped["Valor"] / grouped["Valor"].sum()
    total = float(grouped["Valor"].sum())
    hover = alt.selection_point(fields=["Categoria"], on="pointerover", empty=True)
    arc = (
        alt.Chart(grouped)
        .mark_arc(innerRadius=62, outerRadius=102, cornerRadius=3, padAngle=.012)
        .encode(
            theta=alt.Theta("Valor:Q", stack=True),
            color=alt.Color("Categoria:N", scale=alt.Scale(range=CATEGORY_COLORS), legend=alt.Legend(title=None, orient="right")),
            opacity=alt.condition(hover, alt.value(1), alt.value(.72)),
            tooltip=[
                alt.Tooltip("Categoria:N", title="Categoria"),
                alt.Tooltip("Valor:Q", title="Total", format=",.2f"),
                alt.Tooltip("Participação:Q", title="Participação", format=".1%"),
            ],
        )
        .add_params(hover)
    )
    center = pd.DataFrame([{"Rótulo": "Total", "Total": format_brl(total)}])
    label = alt.Chart(center).mark_text(color=theme["muted"], fontSize=11, dy=-10).encode(text="Rótulo:N")
    value = alt.Chart(center).mark_text(color=theme["text"], fontSize=17, fontWeight=700, dy=12).encode(text="Total:N")
    return (
        alt.layer(arc, label, value)
        .properties(height=275)
        .configure(background=theme["surface"])
        .configure_view(strokeOpacity=0)
        .configure_legend(labelColor=theme["muted"], symbolSize=90)
    )


user = st.session_state.user
summary = user_summary(user["id"])
transactions = transactions_frame(user["id"])
holdings = holdings_frame(user["id"])
first_name = str(user["name"]).split()[0]

page_header(
    f"Olá, {first_name}",
    "Aqui está o resumo da sua vida financeira, com os principais números e próximos passos em um só lugar.",
    eyebrow="Visão geral",
    meta=f"{date.today().day:02d} de {MONTH_NAMES[date.today().month - 1]} de {date.today().year}",
)

with st.container(key="home_toolbar"):
    period_column, status_column, action_column = st.columns([1.2, 2.7, .8], vertical_alignment="bottom")
    with period_column:
        st.selectbox("Período", ["Todo o histórico"], disabled=True, key="home_period")
    with status_column:
        st.caption("Os valores abaixo usam somente os registros da sua conta.")
    with action_column:
        if st.button("Atualizar", icon=":material/refresh:", width="stretch", key="home_refresh"):
            st.rerun()

expense_ratio = summary["expense"] / summary["income"] * 100 if summary["income"] else 0.0
savings = summary["income"] - summary["expense"]
metric_card_grid(
    [
        {"label": "Saldo total", "value": format_brl(summary["balance"]), "delta": "Receitas menos despesas", "icon": "account_balance_wallet", "tone": "green", "delta_tone": "positive" if summary["balance"] >= 0 else "negative"},
        {"label": "Receitas", "value": format_brl(summary["income"]), "delta": "Total registrado", "icon": "trending_up", "tone": "green", "delta_tone": "positive"},
        {"label": "Despesas", "value": format_brl(summary["expense"]), "delta": f"{format_percent(expense_ratio, 0)} da renda", "icon": "trending_down", "tone": "red", "delta_tone": "negative" if summary["expense"] else "neutral"},
        {"label": "Investimentos", "value": str(len(holdings)), "delta": "Ativos acompanhados", "icon": "pie_chart", "tone": "violet", "delta_tone": "positive" if len(holdings) else "neutral"},
    ]
)

monthly = _monthly_flow(transactions)
expenses = transactions.loc[transactions["Tipo"] == "Despesa"] if not transactions.empty else transactions

with st.container(key="home_primary_grid"):
    flow_column, expense_column = st.columns([1.55, 1], gap="medium")
    with flow_column:
        with st.container(border=True, key="home_flow_card"):
            st.subheader("Fluxo de caixa", anchor=False)
            st.caption("Receitas, despesas e saldo acumulado ao longo do tempo.")
            if monthly.empty:
                empty_chart_state("Registre uma receita ou despesa para liberar a evolução mensal.")
            else:
                st.altair_chart(_flow_chart(monthly), width="stretch", key="home_flow_chart", theme=None)
    with expense_column:
        with st.container(border=True, key="home_category_card"):
            st.subheader("Despesas por categoria", anchor=False)
            st.caption("Distribuição dos gastos registrados.")
            if expenses.empty or float(expenses["Valor"].sum()) <= 0:
                empty_chart_state("As categorias aparecerão aqui após a primeira despesa.", icon="donut_large")
            else:
                st.altair_chart(_donut_chart(expenses), width="stretch", key="home_category_chart", theme=None)

has_transactions = not transactions.empty
has_expense = bool((transactions["Tipo"] == "Despesa").any()) if has_transactions else False
steps = [has_transactions, has_expense, not holdings.empty]

with st.container(key="home_lower_grid"):
    recent_column, health_column = st.columns([1.55, 1], gap="medium")
    with recent_column:
        with st.container(border=True, key="home_recent"):
            st.subheader("Transações recentes", anchor=False)
            if transactions.empty:
                st.info("Nenhuma movimentação registrada. Use **Finanças pessoais** para começar.", icon=":material/receipt_long:")
                st.caption("A tabela exibirá data, descrição, categoria, conta e valor.")
            else:
                st.dataframe(
                    transactions.head(6).drop(columns="id"),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    },
                )
    with health_column:
        with st.container(border=True, key="home_health"):
            st.subheader("Seu próximo passo", anchor=False)
            if all(steps):
                ratio = max(0.0, min(savings / summary["income"], 1.0)) if summary["income"] else 0.0
                st.progress(ratio, text=f"Taxa de economia: {format_percent(ratio * 100, 0)}")
                st.success("Sua visão financeira está completa e pronta para acompanhamento.", icon=":material/check_circle:")
            else:
                labels = ["Registrar uma receita", "Adicionar uma despesa", "Cadastrar um investimento"]
                for done, label in zip(steps, labels, strict=True):
                    st.write(f"{':material/check_circle:' if done else ':material/radio_button_unchecked:'} {label}")
                st.progress(sum(steps) / len(steps), text=f"{sum(steps)} de {len(steps)} etapas concluídas")
            st.caption(f"Última leitura: {date.today():%d/%m/%Y}.")
