"""Análise técnica de ativos da B3 e gestão do portfólio virtual."""

import logging

import altair as alt
import pandas as pd
import streamlit as st

from utils.database import delete_holding, holdings_frame, save_holding
from utils.finance import MarketDataError, latest_price, normalize_ticker, prices, quote
from utils.formatting import format_brl, format_decimal, format_percent
from utils.ui import chart_theme, metric_card_grid, page_header


LOGGER = logging.getLogger(__name__)
PERIOD_OPTIONS = {
    "1 mês": "1mo",
    "3 meses": "3mo",
    "6 meses": "6mo",
    "1 ano": "1y",
    "2 anos": "2y",
}

user = st.session_state.user
st.session_state.setdefault("investment_ticker", "PETR4")
st.session_state.setdefault("investment_input_error", None)

@st.dialog("Adicionar ao portfólio", icon=":material/add_chart:")
def add_position(ticker: str, current: float) -> None:
    """Cria ou atualiza uma posição virtual para o ativo selecionado."""
    st.caption(
        f"Ativo selecionado: **{ticker}** · preço atual aproximado: "
        f"**{format_brl(current)}**"
    )
    with st.form("position_form"):
        quantity = st.number_input("Quantidade", min_value=0.01, step=1.0)
        avg_price = st.number_input(
            "Preço médio pago",
            min_value=0.01,
            value=max(current, 0.01),
            step=0.10,
        )
        saved = st.form_submit_button(
            "Salvar no portfólio",
            type="primary",
            icon=":material/save:",
            width="stretch",
        )
    if saved:
        save_holding(user["id"], ticker, float(quantity), float(avg_price))
        st.toast("Posição salva!", icon=":material/check_circle:")
        st.rerun()

page_header(
    "Investimentos",
    "Pesquise ativos da B3, compreenda os indicadores e acompanhe seu portfólio virtual.",
    eyebrow="Mercado e portfólio",
    meta="Dados informativos · não é recomendação",
)
with st.expander("Guia rápido dos indicadores", icon=":material/school:"):
    st.markdown(
        "- **MM20 e MM50:** representam tendências médias de curto e médio prazo.\n"
        "- **RSI:** valores abaixo de 30 podem indicar sobrevenda; valores acima "
        "de 70 podem indicar sobrecompra.\n"
        "- **MACD:** compara médias exponenciais e auxilia na identificação de "
        "mudanças de tendência.\n\n"
        "Os indicadores utilizam dados históricos, não garantem resultados e não "
        "constituem recomendação de investimento."
    )

with st.container(key="investments_toolbar"):
    with st.form("ticker_search", border=False):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            ticker_input = st.text_input(
                "Código de negociação da B3",
                value=st.session_state.investment_ticker,
                placeholder="Ex.: PETR4",
                help="Informe um código negociado na B3, como PETR4 ou BOVA11.",
                max_chars=6,
                key="ticker_input",
            )
            period_label = st.selectbox("Período", list(PERIOD_OPTIONS), index=2)
            searched = st.form_submit_button("Analisar", type="primary", icon=":material/search:")
if searched:
    try:
        cleaned = normalize_ticker(ticker_input)
    except ValueError as exc:
        st.session_state.investment_input_error = str(exc)
    else:
        st.session_state.investment_ticker = cleaned
        st.session_state.investment_input_error = None
ticker = st.session_state.investment_ticker
period = PERIOD_OPTIONS[period_label]

if st.session_state.investment_input_error:
    st.error(st.session_state.investment_input_error, icon=":material/error:")

try:
    # Evita um componente transitório que era removido enquanto extensões do
    # navegador modificavam o DOM, causando o erro `removeChild` do React.
    data = prices(ticker, period)
    snapshot = quote(ticker)
    history_source = str(data["Fonte"].iloc[-1])
    if bool(data["Demonstração"].iloc[-1]) or snapshot["demo"]:
        st.warning(
            "As fontes de dados não responderam. Os valores identificados como "
            "demonstração não representam o mercado.",
            icon=":material/cloud_off:",
        )
    elif snapshot["source"] != "brapi.dev" or history_source != "brapi.dev":
        st.info(
            "A brapi.dev não forneceu todos os dados. Parte da consulta foi "
            "obtida pela fonte alternativa.",
            icon=":material/sync:",
        )
    last = float(snapshot["price"])
    change = snapshot["change_percent"]
    if change is None:
        previous = float(data["Close"].iloc[-2])
        change = (last / previous - 1) * 100
    rsi = float(data["RSI"].iloc[-1])
    macd = float(data["MACD"].iloc[-1])
    source_label = (
        snapshot["source"]
        if snapshot["source"] == history_source
        else f"{snapshot['source']} · histórico: {history_source}"
    )
    st.badge(
        f"Fonte: {source_label}",
        icon=":material/database:",
        color="green" if snapshot["source"] == "brapi.dev" else "orange",
    )
    if snapshot["updated_at"]:
        updated = pd.to_datetime(snapshot["updated_at"], utc=True).tz_convert("America/Sao_Paulo")
        st.caption(
            f"Última atualização informada pela fonte: "
            f"{updated:%d/%m/%Y às %H:%M} (horário de Brasília)."
        )
    metric_card_grid(
        [
            {"label": ticker, "value": format_brl(last), "delta": format_percent(change, 2), "icon": "show_chart", "tone": "blue", "delta_tone": "positive" if change >= 0 else "negative"},
            {"label": "RSI (14)", "value": format_decimal(rsi, 1) if pd.notna(rsi) else "—", "delta": "Força relativa", "icon": "speed", "tone": "cyan"},
            {"label": "MACD", "value": format_decimal(macd, 3), "delta": "Tendência", "icon": "ssid_chart", "tone": "violet"},
            {"label": "Volume", "value": f"{format_decimal(float(snapshot['volume']) / 1e6, 1)} mi", "delta": "Negociação informada", "icon": "bar_chart", "tone": "green"},
        ]
    )
    if st.button(
        "Adicionar este ativo ao meu portfólio",
        icon=":material/add_chart:",
        type="primary",
    ):
        add_position(ticker, last)
    lines = data.melt(
        id_vars=[data.columns[0]],
        value_vars=["Close", "MM20", "MM50"],
        var_name="Série",
        value_name="Preço",
    )
    lines["Série"] = lines["Série"].replace({"Close": "Fechamento"})
    date_col = data.columns[0]
    price_area = (
        alt.Chart(data)
        .mark_area(color="#60A5FA", opacity=0.13, interpolate="monotone")
        .encode(
            x=alt.X(f"{date_col}:T", title=None),
            y=alt.Y("Close:Q", title="Preço (R$)", scale=alt.Scale(zero=False)),
        )
    )
    trend_lines = (
        alt.Chart(lines)
        .mark_line(strokeWidth=2.5, interpolate="monotone")
        .encode(
            x=alt.X(f"{date_col}:T", title=None),
            y=alt.Y("Preço:Q", title="Preço (R$)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "Série:N",
                scale=alt.Scale(
                    domain=["Fechamento", "MM20", "MM50"],
                    range=["#60A5FA", "#FBBF24", "#8176FF"],
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{date_col}:T", format="%d/%m/%Y"),
                "Série:N",
                alt.Tooltip("Preço:Q", format=".2f"),
            ],
        )
    )
    theme = chart_theme()
    chart = (
        alt.layer(price_area, trend_lines)
        .properties(height=380)
        .interactive(bind_y=False)
        .configure(background=theme["surface"])
        .configure_view(strokeOpacity=0)
        .configure_axis(
            gridColor=theme["grid"],
            gridOpacity=0.28,
            labelColor=theme["muted"],
            titleColor=theme["muted"],
        )
        .configure_legend(labelColor=theme["muted"], orient="top")
    )
    with st.container(border=True):
        st.subheader("Preço e médias móveis", anchor=False)
        st.altair_chart(chart, key="price_moving_averages_chart", theme=None)
    a, b = st.columns(2)
    with a.container(border=True):
        st.subheader("RSI", anchor=False)
        st.line_chart(data, x=date_col, y="RSI", y_label="Índice", x_label=None)
    with b.container(border=True):
        st.subheader("MACD e linha de sinal", anchor=False)
        st.line_chart(data, x=date_col, y=["MACD", "Sinal"], x_label=None)
except (MarketDataError, ValueError) as exc:
    st.error(str(exc), icon=":material/error:")
except Exception:
    LOGGER.exception("Falha inesperada ao analisar o ativo %s", ticker)
    st.error(
        "Não foi possível concluir a análise deste ativo. Tente novamente mais tarde.",
        icon=":material/error:",
    )

st.subheader("Meu portfólio virtual", anchor=False)
portfolio = holdings_frame(user["id"])
if portfolio.empty:
    st.info(
        "Você ainda não acompanha nenhum investimento. Pesquise um ativo e "
        "adicione sua posição.",
        icon=":material/query_stats:",
    )
else:
    current = []
    with st.spinner("Atualizando sua carteira…"):
        for symbol in portfolio["Ativo"]:
            try:
                current.append(latest_price(symbol))
            except Exception:
                LOGGER.warning("Não foi possível atualizar o ativo %s", symbol)
                current.append(float("nan"))
    portfolio["Preço atual"] = current
    portfolio["Investido"] = portfolio["Quantidade"] * portfolio["Preço médio"]
    portfolio["Patrimônio"] = portfolio["Quantidade"] * portfolio["Preço atual"]
    portfolio["Resultado"] = portfolio["Patrimônio"] - portfolio["Investido"]
    portfolio_columns = st.columns(2, gap="medium")
    with portfolio_columns[0]:
        st.metric(
            "Patrimônio estimado",
            format_brl(portfolio["Patrimônio"].sum()),
            border=True,
        )
    with portfolio_columns[1]:
        st.metric(
            "Resultado não realizado",
            format_brl(portfolio["Resultado"].sum()),
            border=True,
        )
    money_columns = [
        "Preço médio",
        "Preço atual",
        "Investido",
        "Patrimônio",
        "Resultado",
    ]
    st.dataframe(
        portfolio.drop(columns="id"),
        hide_index=True,
        column_config={
            column: st.column_config.NumberColumn(format="R$ %.2f")
            for column in money_columns
        },
        key="investment_portfolio_table",
    )
    with st.popover("Remover posição", icon=":material/delete:"):
        choices = {row.Ativo: int(row.id) for row in portfolio.itertuples()}
        choice = st.selectbox("Ativo", list(choices))
        if st.button(
            "Confirmar remoção",
            type="primary",
            icon=":material/delete_forever:",
        ):
            delete_holding(user["id"], choices[choice])
            st.toast("Posição removida.")
            st.rerun()

st.caption(
    "Fonte principal: brapi.dev. O Yahoo Finance é utilizado somente como "
    "contingência. A frequência e o atraso dependem do mercado e do plano "
    "contratado. Conteúdo educacional, sem recomendação de investimento."
)
