"""Chat local da Central de Ajuda do FinScope Beta 5.1."""

import streamlit as st

from utils.help_assistant import answer_help_question


SUGGESTIONS = {
    ":blue[:material/receipt_long:] Como registrar uma despesa?": (
        "Como registrar uma despesa?"
    ),
    ":green[:material/query_stats:] Como analisar um ativo?": (
        "Como analisar um ativo da B3?"
    ),
    ":violet[:material/account_circle:] Como recuperar a senha?": (
        "Como recuperar minha senha?"
    ),
    ":orange[:material/shield:] Meus dados estão seguros?": (
        "Como funciona a privacidade dos meus dados?"
    ),
}

st.session_state.setdefault("help_messages", [])
st.session_state.setdefault("help_pending_prompt", None)

st.title("Central de ajuda")
st.write(
    "Converse com o guia do FinScope para aprender a utilizar as funcionalidades "
    "da plataforma."
)

with st.container(horizontal=True):
    st.badge("Ajuda disponível", icon=":material/help_center:", color="green")
    st.badge("Sem inteligência artificial", icon=":material/offline_bolt:", color="blue")

st.caption(
    "Este chat utiliza respostas locais e pré-revisadas. Nenhuma pergunta ou "
    "informação da sua conta é enviada a serviços de inteligência artificial."
)

if not st.session_state.help_messages:
    st.info(
        "Escolha uma sugestão ou escreva sua dúvida no campo abaixo.",
        icon=":material/lightbulb:",
    )
    selected = st.pills(
        "Sugestões",
        list(SUGGESTIONS),
        label_visibility="collapsed",
    )
    if selected:
        st.session_state.help_pending_prompt = SUGGESTIONS[selected]
        st.rerun()

for message in st.session_state.help_messages:
    avatar = ":material/help_center:" if message["role"] == "assistant" else None
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])

typed_prompt = st.chat_input("Digite sua dúvida sobre o FinScope")
prompt = st.session_state.pop("help_pending_prompt", None) or typed_prompt
if prompt:
    st.session_state.help_messages.append({"role": "user", "content": prompt})
    st.session_state.help_messages.append(
        {"role": "assistant", "content": answer_help_question(prompt)}
    )
    st.rerun()

if st.session_state.help_messages:
    if st.button("Limpar conversa", icon=":material/delete_sweep:"):
        st.session_state.help_messages = []
        st.rerun()

with st.expander("Limites desta central", icon=":material/info:"):
    st.write(
        "A Central de Ajuda explica as funcionalidades existentes, mas não analisa "
        "a situação individual da sua conta e não fornece recomendação de compra "
        "ou venda de investimentos."
    )
