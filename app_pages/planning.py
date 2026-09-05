"""Orçamentos, metas, recorrências e calendário financeiro."""

from datetime import date

import pandas as pd
import streamlit as st

from utils.database import (
    TRANSACTION_CATEGORIES,
    budgets_frame,
    confirm_recurring_entry,
    create_goal,
    create_recurring_entry,
    delete_budget,
    delete_goal,
    delete_recurring_entry,
    goals_frame,
    recurring_frame,
    save_budget,
    set_recurring_active,
    transactions_frame,
    update_goal_amount,
)
from utils.formatting import format_brl
from utils.ui import metric_card_grid, page_header


def _quantity_label(total: int, singular: str, plural: str) -> str:
    return f"{total} {singular if total == 1 else plural}"


def _progress_money(value: float) -> str:
    """Escapa o cifrão em textos Markdown internos do progresso."""
    return format_brl(value).replace("$", r"\$")


user = st.session_state.user


@st.dialog("Novo orçamento", icon=":material/account_balance:")
def new_budget() -> None:
    """Cria ou substitui o limite mensal de uma categoria."""
    with st.form("new_budget_form"):
        category = st.selectbox("Categoria", TRANSACTION_CATEGORIES["Despesa"])
        limit = st.number_input("Limite mensal (R$)", min_value=1.0, step=50.0)
        submitted = st.form_submit_button("Salvar orçamento", type="primary", width="stretch")
    if submitted:
        save_budget(user["id"], category, float(limit))
        st.toast("Orçamento salvo.", icon=":material/check_circle:")
        st.rerun()


@st.dialog("Nova meta", icon=":material/flag:")
def new_goal() -> None:
    """Coleta e valida uma nova meta financeira."""
    with st.form("new_goal_form"):
        name = st.text_input("Nome da meta", placeholder="Ex.: reserva de emergência", max_chars=80)
        target = st.number_input("Valor objetivo (R$)", min_value=1.0, step=100.0)
        saved = st.number_input("Valor já guardado (R$)", min_value=0.0, step=100.0)
        has_deadline = st.checkbox("Definir prazo")
        deadline = st.date_input("Prazo", min_value=date.today(), disabled=not has_deadline)
        submitted = st.form_submit_button("Criar meta", type="primary", width="stretch")
    if submitted:
        try:
            create_goal(user["id"], name, float(target), float(saved), deadline if has_deadline else None)
            st.toast("Meta criada.", icon=":material/check_circle:")
            st.rerun()
        except ValueError as error:
            st.error(str(error))


@st.dialog("Novo lançamento recorrente", icon=":material/event_repeat:")
def new_recurring() -> None:
    """Cadastra uma previsão que dependerá de confirmação mensal."""
    kind = st.segmented_control("Tipo", ["Receita", "Despesa"], default="Despesa")
    with st.form("new_recurring_form"):
        category = st.selectbox("Categoria", TRANSACTION_CATEGORIES[kind])
        amount = st.number_input("Valor (R$)", min_value=0.01, step=10.0)
        day = st.number_input("Dia do mês", min_value=1, max_value=28, value=5, step=1)
        description = st.text_input("Descrição", placeholder="Ex.: aluguel", max_chars=160)
        submitted = st.form_submit_button("Salvar recorrência", type="primary", width="stretch")
    if submitted:
        create_recurring_entry(user["id"], kind, float(amount), category, description, int(day))
        st.toast("Recorrência salva.", icon=":material/check_circle:")
        st.rerun()


page_header(
    "Planejamento",
    "Defina limites, acompanhe objetivos e organize os compromissos do mês.",
    eyebrow="Planos e objetivos",
    meta="Orçamentos, metas e recorrências",
)

budgets = budgets_frame(user["id"])
goals = goals_frame(user["id"])
recurring = recurring_frame(user["id"])
month_start = date.today().replace(day=1)
month_transactions = transactions_frame(user["id"], month_start)

budget_limit = float(budgets["Limite"].sum()) if not budgets.empty else 0.0
goal_saved = float(goals["Guardado"].sum()) if not goals.empty else 0.0
active_recurring = recurring[recurring["Ativa"]] if not recurring.empty else recurring
recurring_total = float(active_recurring["Valor"].sum()) if not active_recurring.empty else 0.0
metric_card_grid(
    [
        {"label": "Limites mensais", "value": format_brl(budget_limit), "delta": _quantity_label(len(budgets), "categoria", "categorias"), "icon": "account_balance", "tone": "blue"},
        {"label": "Guardado em metas", "value": format_brl(goal_saved), "delta": _quantity_label(len(goals), "objetivo", "objetivos"), "icon": "flag", "tone": "green", "delta_tone": "positive" if goal_saved else "neutral"},
        {"label": "Recorrências ativas", "value": format_brl(recurring_total), "delta": _quantity_label(len(active_recurring), "compromisso", "compromissos"), "icon": "event_repeat", "tone": "violet"},
        {"label": "Movimentações no mês", "value": str(len(month_transactions)), "delta": "Registros confirmados", "icon": "calendar_month", "tone": "cyan"},
    ]
)

budget_tab, goal_tab, recurring_tab, calendar_tab = st.tabs(
    ["Orçamentos", "Metas", "Recorrências", "Calendário"]
)

with budget_tab:
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.subheader("Orçamento mensal", anchor=False)
        if st.button("Adicionar orçamento", icon=":material/add:", key="open_budget"):
            new_budget()
    if budgets.empty:
        st.info("Defina um limite para uma categoria de despesa.", icon=":material/info:")
    else:
        for row in budgets.itertuples():
            ratio = min(max(float(row.Gasto) / float(row.Limite), 0), 1.0)
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"#### {row.Categoria}")
                    st.progress(ratio, text=f"{_progress_money(row.Gasto)} de {_progress_money(row.Limite)}")
                    if row.Disponível < 0:
                        st.error(f"Limite excedido em {format_brl(abs(row.Disponível))}.")
                    else:
                        st.caption(f"Ainda disponível: {format_brl(row.Disponível)}")
                with right:
                    if st.button("Excluir", icon=":material/delete:", key=f"budget_delete_{row.id}"):
                        delete_budget(user["id"], int(row.id))
                        st.rerun()

with goal_tab:
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.subheader("Metas financeiras", anchor=False)
        if st.button("Adicionar meta", icon=":material/add:", key="open_goal"):
            new_goal()
    if goals.empty:
        st.info("Crie uma meta para acompanhar seu progresso.", icon=":material/flag:")
    else:
        for row in goals.itertuples():
            with st.container(border=True):
                st.markdown(f"#### {row.Meta}")
                st.progress(float(row.Progresso), text=f"{_progress_money(row.Guardado)} de {_progress_money(row.Objetivo)}")
                if row.Prazo:
                    st.caption(f"Prazo: {row.Prazo:%d/%m/%Y}")
                amount = st.number_input(
                    "Total guardado (R$)",
                    min_value=0.0,
                    max_value=float(row.Objetivo),
                    value=float(row.Guardado),
                    key=f"goal_amount_{row.id}",
                )
                save_col, delete_col = st.columns(2)
                if save_col.button("Atualizar", icon=":material/save:", key=f"goal_save_{row.id}"):
                    update_goal_amount(user["id"], int(row.id), float(amount))
                    st.rerun()
                if delete_col.button("Excluir", icon=":material/delete:", key=f"goal_delete_{row.id}"):
                    delete_goal(user["id"], int(row.id))
                    st.rerun()

with recurring_tab:
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.subheader("Lançamentos recorrentes", anchor=False)
        if st.button("Adicionar recorrência", icon=":material/add:", key="open_recurring"):
            new_recurring()
    if recurring.empty:
        st.info("Cadastre salário, aluguel ou outro compromisso mensal.", icon=":material/event_repeat:")
    else:
        for row in recurring.itertuples():
            with st.container(border=True):
                st.markdown(f"**Dia {row.Dia} · {row.Categoria} · {format_brl(row.Valor)}**")
                st.caption(row.Descrição or f"{row.Tipo} recorrente")
                confirm_col, status_col, delete_col = st.columns(3)
                occurrence_date = date.today().replace(day=int(row.Dia))
                if confirm_col.button(
                    "Confirmar neste mês",
                    icon=":material/check:",
                    disabled=not bool(row.Ativa) or occurrence_date > date.today(),
                    key=f"rec_confirm_{row.id}",
                ):
                    ok, message = confirm_recurring_entry(user["id"], int(row.id), occurrence_date)
                    (st.toast if ok else st.warning)(message)
                    if ok:
                        st.rerun()
                if occurrence_date > date.today() and bool(row.Ativa):
                    st.caption(
                        f"A confirmação ficará disponível em {occurrence_date:%d/%m/%Y}."
                    )
                new_status = status_col.toggle("Ativa", value=bool(row.Ativa), key=f"rec_active_{row.id}")
                if new_status != bool(row.Ativa):
                    set_recurring_active(user["id"], int(row.id), new_status)
                    st.rerun()
                if delete_col.button("Excluir", icon=":material/delete:", key=f"rec_delete_{row.id}"):
                    delete_recurring_entry(user["id"], int(row.id))
                    st.rerun()

with calendar_tab:
    st.subheader("Calendário financeiro do mês", anchor=False)
    transactions = month_transactions
    events: list[dict[str, object]] = []
    if not transactions.empty:
        for row in transactions.itertuples():
            events.append(
                {
                    "Data": row.Data,
                    "Situação": "Confirmado",
                    "Tipo": row.Tipo,
                    "Descrição": row.Descrição or row.Categoria,
                    "Valor": row.Valor,
                }
            )
    if not recurring.empty:
        for row in recurring[recurring["Ativa"]].itertuples():
            events.append(
                {
                    "Data": date.today().replace(day=int(row.Dia)),
                    "Situação": "Previsto",
                    "Tipo": row.Tipo,
                    "Descrição": row.Descrição or row.Categoria,
                    "Valor": row.Valor,
                }
            )
    if not events:
        st.info("Ainda não há eventos para este mês.", icon=":material/calendar_month:")
    else:
        calendar = pd.DataFrame(events).sort_values(["Data", "Situação"])
        st.dataframe(
            calendar,
            hide_index=True,
            column_config={
                "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
        st.caption("Itens previstos não alteram o saldo até serem confirmados.")
