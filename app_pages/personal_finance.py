"""Gestão de receitas e despesas da conta autenticada."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from utils.database import (
    TRANSACTION_CATEGORIES,
    add_transaction,
    delete_transaction,
    transactions_frame,
    user_summary,
)
from utils.formatting import format_brl, format_percent


user = st.session_state.user
FLOW_COLORS = ["#22C55E", "#FB7185"]
CATEGORY_COLORS = [
    "#60A5FA",
    "#A78BFA",
    "#22D3EE",
    "#34D399",
    "#FBBF24",
    "#FB7185",
    "#818CF8",
    "#2DD4BF",
]


def _flow_area_chart(flow):
    """Cria uma leitura temporal suave, interativa e fiel às cores financeiras."""
    base = alt.Chart(flow).encode(
        x=alt.X(
            "Data:T",
            title=None,
            axis=alt.Axis(format="%d/%m", labelAngle=0, tickCount=6),
        ),
        y=alt.Y("Valor:Q", title="Valor (R$)", stack=None),
        color=alt.Color(
            "Tipo:N",
            scale=alt.Scale(domain=["Receita", "Despesa"], range=FLOW_COLORS),
            legend=alt.Legend(title=None, orient="top", direction="horizontal"),
        ),
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("Tipo:N", title="Tipo"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f"),
        ],
    )
    area = base.mark_area(opacity=0.12, interpolate="monotone")
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


def _expense_donut_chart(expenses):
    """Apresenta participação por categoria com total central e destaque ao passar o cursor."""
    frame = expenses.copy()
    total = float(frame["Valor"].sum())
    frame["Participação"] = frame["Valor"] / total
    hover = alt.selection_point(
        fields=["Categoria"],
        on="pointerover",
        empty=True,
    )
    arc = (
        alt.Chart(frame)
        .mark_arc(innerRadius=72, outerRadius=118, cornerRadius=6, padAngle=0.018)
        .encode(
            theta=alt.Theta("Valor:Q", stack=True),
            color=alt.Color(
                "Categoria:N",
                scale=alt.Scale(range=CATEGORY_COLORS),
                legend=alt.Legend(title=None, orient="bottom", columns=2),
            ),
            opacity=alt.condition(hover, alt.value(1), alt.value(0.46)),
            tooltip=[
                alt.Tooltip("Categoria:N", title="Categoria"),
                alt.Tooltip("Valor:Q", title="Total", format=",.2f"),
                alt.Tooltip("Participação:Q", title="Participação", format=".1%"),
            ],
        )
        .add_params(hover)
    )
    center = pd.DataFrame(
        [{"Rótulo": "Total", "Total": format_brl(total)}]
    )
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


@st.dialog("Novo lançamento", icon=":material/add_card:")
def new_transaction() -> None:
    """Coleta e salva uma nova receita ou despesa da conta atual."""
    kind = st.segmented_control(
        "O que você deseja registrar?",
        ["Receita", "Despesa"],
        default="Despesa",
        key="new_kind",
    )
    with st.form("new_transaction_form"):
        category = st.selectbox(
            "Categoria",
            TRANSACTION_CATEGORIES[kind],
            key=f"new_category_{kind.lower()}",
        )
        amount = st.number_input(
            "Valor (R$)",
            min_value=0.01,
            max_value=999_999_999.99,
            step=10.0,
            format="%.2f",
        )
        occurred = st.date_input(
            "Data",
            value=date.today(),
            max_value=date.today(),
        )
        description = st.text_input(
            "Descrição (opcional)",
            placeholder="Ex.: supermercado da semana",
            max_chars=160,
        )
        saved = st.form_submit_button(
            "Salvar lançamento",
            type="primary",
            icon=":material/save:",
            width="stretch",
        )
    if saved:
        add_transaction(
            user["id"],
            kind,
            float(amount),
            category,
            description,
            occurred,
        )
        st.toast("Lançamento salvo.", icon=":material/check_circle:")
        st.rerun()


st.title("Finanças pessoais")
with st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
):
    st.write(
        "Registre suas receitas e despesas. Os investimentos permanecem em uma "
        "área separada."
    )
    if st.button("Novo lançamento", type="primary", icon=":material/add:"):
        new_transaction()

with st.expander("Como usar esta área", icon=":material/help:"):
    st.markdown(
        "1. Selecione **Novo lançamento**.\n"
        "2. Escolha **Receita** ou **Despesa**.\n"
        "3. Informe a categoria, o valor e a data.\n\n"
        "O resumo e os gráficos serão atualizados automaticamente."
    )

data = transactions_frame(user["id"])
summary = user_summary(user["id"])
metric_columns = st.columns(4, gap="medium")
with metric_columns[0]:
    st.metric("Saldo", format_brl(summary["balance"]), border=True)
with metric_columns[1]:
    st.metric("Total recebido", format_brl(summary["income"]), border=True)
with metric_columns[2]:
    st.metric("Total gasto", format_brl(summary["expense"]), border=True)
savings = summary["balance"] / summary["income"] * 100 if summary["income"] else 0
with metric_columns[3]:
    st.metric("Taxa de economia", format_percent(savings), border=True)

if data.empty:
    st.info(
        "Ainda não há lançamentos. Comece registrando sua renda ou sua primeira "
        "despesa.",
        icon=":material/receipt_long:",
    )
    st.stop()

with st.popover("Filtrar lançamentos", icon=":material/filter_list:"):
    selected_types = st.pills(
        "Tipos",
        ["Receita", "Despesa"],
        default=["Receita", "Despesa"],
        selection_mode="multi",
    )
    available_categories = sorted(data["Categoria"].unique())
    selected_categories = st.multiselect(
        "Categorias",
        available_categories,
        default=available_categories,
    )

filtered = data[
    data["Tipo"].isin(selected_types or [])
    & data["Categoria"].isin(selected_categories)
]

left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.subheader("Fluxo ao longo do tempo", anchor=False)
        flow = filtered.groupby(["Data", "Tipo"], as_index=False)["Valor"].sum()
        if flow.empty:
            st.caption("Nenhum lançamento corresponde aos filtros selecionados.")
        else:
            st.altair_chart(_flow_area_chart(flow), width="stretch")

with right:
    with st.container(border=True):
        st.subheader("Despesas por categoria", anchor=False)
        expenses = (
            filtered[filtered["Tipo"] == "Despesa"]
            .groupby("Categoria", as_index=False)["Valor"]
            .sum()
            .sort_values("Valor", ascending=False)
        )
        if expenses.empty:
            st.caption("Adicione despesas para visualizar a distribuição.")
        else:
            st.altair_chart(_expense_donut_chart(expenses), width="stretch")

with st.container(border=True):
    st.subheader("Seus lançamentos", anchor=False)
    st.dataframe(
        filtered.drop(columns="id"),
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
        key="transactions_table",
    )
    with st.popover("Excluir um lançamento", icon=":material/delete:"):
        choices = {
            (
                f"{row.Tipo} · {row.Categoria} · {format_brl(row.Valor)} · "
                f"{row.Data:%d/%m/%Y}"
            ): int(row.id)
            for row in data.itertuples()
        }
        choice = st.selectbox(
            "Selecione um lançamento",
            list(choices),
            key="delete_transaction_choice",
        )
        if st.button(
            "Confirmar exclusão",
            type="primary",
            icon=":material/delete_forever:",
        ):
            delete_transaction(user["id"], choices[choice])
            st.toast("Lançamento excluído.")
            st.rerun()
