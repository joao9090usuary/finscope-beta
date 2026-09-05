"""Central de Ajuda local do Revo."""

import streamlit as st

from utils.help_assistant import answer_help_question
from utils.ui import page_header


SUGGESTIONS = {
    ":blue[:material/receipt_long:] Registrar uma despesa": (
        "Como registrar uma despesa?"
    ),
    ":green[:material/query_stats:] Analisar um ativo da B3": (
        "Como analisar um ativo da B3?"
    ),
    ":violet[:material/lock_reset:] Recuperar minha senha": (
        "Como recuperar minha senha?"
    ),
    ":orange[:material/shield:] Entender a privacidade": (
        "Como funciona a privacidade dos meus dados?"
    ),
}

st.session_state.setdefault("help_messages", [])
st.session_state.setdefault("help_pending_prompt", None)


def _queue_selected_suggestion() -> None:
    """Agenda uma sugestão uma única vez, sem criar um ciclo de reruns."""
    selected = st.session_state.get("help_suggestions")
    if selected in SUGGESTIONS:
        st.session_state.help_pending_prompt = SUGGESTIONS[selected]

page_header(
    "Central de ajuda",
    "Encontre uma orientação rápida para usar o Revo com confiança.",
    eyebrow="Suporte",
    meta="Respostas locais e pré-revisadas",
)

topics, conversation = st.columns([1, 2.15], gap="medium")

with topics:
    with st.container(border=True, key="help_topics"):
        st.subheader("Comece por uma tarefa", anchor=False)
        st.caption("Selecione um assunto ou escreva sua própria dúvida.")
        selected = st.pills(
            "Assuntos sugeridos",
            list(SUGGESTIONS),
            label_visibility="collapsed",
            key="help_suggestions",
            on_change=_queue_selected_suggestion,
        )

        st.info(
            "Sua pergunta permanece nesta sessão e não é enviada a serviços de inteligência artificial.",
            icon=":material/verified_user:",
        )
        with st.expander("O que esta central pode responder?", icon=":material/info:"):
            st.write(
                "A Central de Ajuda explica as funcionalidades existentes. Ela não "
                "analisa sua situação individual e não recomenda compra ou venda de ativos."
            )

with conversation:
    with st.container(border=True, key="help_conversation"):
        st.subheader("Converse com o guia", anchor=False)
        if not st.session_state.help_messages:
            st.caption(
                "Exemplo: “Como adiciono meu salário?” ou “Onde baixo meu relatório em PDF?”"
            )

        for message in st.session_state.help_messages:
            avatar = ":material/help_center:" if message["role"] == "assistant" else None
            with st.chat_message(message["role"], avatar=avatar):
                st.write(message["content"])

        typed_prompt = st.chat_input(
            "Digite sua dúvida sobre o Revo",
            key="help_chat_input",
            submit_mode="disable",
        )
        prompt = st.session_state.pop("help_pending_prompt", None) or typed_prompt
        if prompt:
            st.session_state.help_messages.append({"role": "user", "content": prompt})
            st.session_state.help_messages.append(
                {"role": "assistant", "content": answer_help_question(prompt)}
            )
            st.rerun()

        if st.session_state.help_messages:
            if st.button(
                "Limpar conversa",
                icon=":material/delete_sweep:",
                type="tertiary",
            ):
                st.session_state.help_messages = []
                st.rerun()
