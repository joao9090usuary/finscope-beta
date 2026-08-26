"""Preferências, portabilidade e controles de privacidade da conta."""

from datetime import datetime, timedelta

import streamlit as st

from utils.data_portability import build_account_export, import_transactions_csv
from utils.database import delete_user_account, get_user_preference, set_weekly_summary, user_summary
from utils.email_service import send_weekly_summary_email


user = st.session_state.user
preference = get_user_preference(user["id"])

st.title("Minha conta")
st.write("Gerencie comunicações, cópias dos seus dados e privacidade.")

notification_tab, data_tab, install_tab, privacy_tab = st.tabs(
    ["Comunicações", "Meus dados", "Instalar", "Privacidade"]
)

with notification_tab:
    st.subheader("Resumo semanal", anchor=False)
    enabled = st.toggle(
        "Receber um resumo financeiro por e-mail",
        value=bool(preference["weekly_summary_enabled"]),
        help="O e-mail contém apenas totais agregados dos últimos sete dias.",
    )
    if enabled != bool(preference["weekly_summary_enabled"]):
        set_weekly_summary(user["id"], enabled)
        st.toast("Preferência atualizada.", icon=":material/check_circle:")
        st.rerun()
    if st.button("Enviar resumo de teste", icon=":material/send:", disabled=not enabled):
        result = send_weekly_summary_email(
            user["email"],
            user["name"],
            user_summary(user["id"], datetime.now().date() - timedelta(days=6)),
        )
        (st.success if result.sent else st.warning)(result.message)
    st.caption("A entrega depende de um provedor SMTP real na hospedagem.")

with data_tab:
    st.subheader("Exportar uma cópia", anchor=False)
    st.write("Baixe lançamentos, investimentos, metas, orçamentos, recorrências e feedbacks.")
    archive = build_account_export(user)
    st.download_button(
        "Baixar meus dados (.zip)",
        data=archive,
        file_name=f"finscope-dados-{datetime.now():%Y-%m-%d}.zip",
        mime="application/zip",
        icon=":material/download:",
        type="primary",
    )
    st.divider()
    st.subheader("Importar lançamentos", anchor=False)
    st.caption("CSV com as colunas Tipo, Valor, Categoria, Descrição e Data; limite de mil linhas.")
    uploaded = st.file_uploader("Selecione o CSV", type=["csv"])
    if st.button("Importar arquivo", icon=":material/upload:", disabled=uploaded is None):
        try:
            imported, errors = import_transactions_csv(user["id"], uploaded.getvalue())
            st.success(f"{imported} lançamento(s) importado(s).")
            if errors:
                st.warning("Algumas linhas foram ignoradas:\n\n" + "\n".join(f"- {item}" for item in errors))
        except ValueError as error:
            st.error(str(error))

with install_tab:
    st.subheader("Leve o FinScope com você", anchor=False)
    st.write(
        "Depois de publicado com HTTPS, abra o menu do navegador e selecione "
        "**Instalar FinScope** ou **Adicionar à tela inicial**."
    )
    st.info(
        "O aplicativo instalado continua usando a mesma conta e o mesmo banco de dados. "
        "A conexão com a internet ainda é necessária.",
        icon=":material/install_mobile:",
    )

with privacy_tab:
    st.subheader("Exclusão permanente", anchor=False)
    st.warning(
        "Esta ação apaga sua conta, lançamentos, portfólio, dashboard, metas, "
        "orçamentos, recorrências e feedbacks. Não é possível desfazer.",
        icon=":material/warning:",
    )
    confirmation = st.text_input("Para confirmar, digite EXCLUIR MINHA CONTA")
    acknowledged = st.checkbox("Entendo que a exclusão é permanente.")
    if st.button(
        "Excluir minha conta",
        type="primary",
        icon=":material/delete_forever:",
        disabled=confirmation != "EXCLUIR MINHA CONTA" or not acknowledged,
    ):
        delete_user_account(user["id"])
        st.session_state.clear()
        st.rerun()
