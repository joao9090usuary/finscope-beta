"""Ponto de entrada, autenticação e navegação do FinScope Beta 5.2.

A versão atual mantém a recuperação de senha por e-mail, mas não exige a
verificação do endereço eletrônico para permitir o acesso. A estrutura de
verificação permanece isolada na camada de serviços para uma versão futura.
"""

from html import escape

import streamlit as st
from sqlalchemy.exc import OperationalError

from utils.database import (
    authenticate,
    authenticated_user,
    create_user,
    get_dashboard,
    init_db,
    reset_password_token,
)
from utils.email_service import (
    DeliveryResult,
    send_feedback_email,
    send_password_reset_email,
)

st.set_page_config(
    page_title="FinScope",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
)

MOBILE_NAVIGATION_JS = r"""
export default function(component) {
    const root = component.parentElement instanceof ShadowRoot
        ? component.parentElement.host
        : component.parentElement;
    const wrapper = root?.closest('[data-testid="stElementContainer"]');
    if (wrapper) {
        wrapper.style.display = "none";
    }

    let tracking = false;
    let startX = 0;
    let startY = 0;
    let startedAt = 0;

    const isMobile = () => window.matchMedia("(max-width: 900px)").matches;
    const isInteractive = (target) => Boolean(target?.closest(
        'input, textarea, select, button, a, [contenteditable="true"], '
        + '[role="slider"], canvas, [data-testid="stDataFrame"]'
    ));

    const findSidebarButton = () => {
        const direct = document.querySelector(
            '[data-testid="stSidebarCollapsedControl"] button, '
            + 'button[data-testid="stSidebarCollapsedControl"]'
        );
        if (direct) return direct;

        return Array.from(document.querySelectorAll("button")).find((button) => {
            const description = [
                button.getAttribute("aria-label") || "",
                button.getAttribute("title") || "",
                button.textContent || "",
            ].join(" ").toLowerCase();
            return description.includes("open sidebar")
                || description.includes("abrir barra lateral")
                || description.includes("keyboard_double_arrow_right");
        });
    };

    const onTouchStart = (event) => {
        if (!isMobile() || event.touches.length !== 1 || isInteractive(event.target)) {
            tracking = false;
            return;
        }
        const touch = event.touches[0];
        tracking = touch.clientX <= 84;
        startX = touch.clientX;
        startY = touch.clientY;
        startedAt = performance.now();
    };

    const onTouchEnd = (event) => {
        if (!tracking || event.changedTouches.length !== 1) return;
        tracking = false;
        const touch = event.changedTouches[0];
        const horizontalDistance = touch.clientX - startX;
        const verticalDistance = Math.abs(touch.clientY - startY);
        const duration = performance.now() - startedAt;

        if (horizontalDistance >= 72 && verticalDistance <= 56 && duration <= 800) {
            findSidebarButton()?.click();
        }
    };

    const onTouchCancel = () => {
        tracking = false;
    };

    document.addEventListener("touchstart", onTouchStart, { passive: true });
    document.addEventListener("touchend", onTouchEnd, { passive: true });
    document.addEventListener("touchcancel", onTouchCancel, { passive: true });

    return () => {
        document.removeEventListener("touchstart", onTouchStart);
        document.removeEventListener("touchend", onTouchEnd);
        document.removeEventListener("touchcancel", onTouchCancel);
    };
}
"""

mobile_navigation_gesture = st.components.v2.component(
    "finscope_mobile_navigation_gesture",
    js=MOBILE_NAVIGATION_JS,
)

st.session_state.setdefault("user", None)
st.session_state.setdefault("help_messages", [])
st.session_state.setdefault("help_pending_prompt", None)
st.session_state.setdefault("flash", None)


def apply_auth_layout() -> None:
    """Mantém a autenticação compacta, centralizada e sem rolagem lateral."""
    st.html(
        """
        <style>
            *, *::before, *::after {
                box-sizing: border-box;
            }

            html, body, #root,
            [data-testid="stApp"],
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                width: 100%;
                max-width: 100%;
                height: 100dvh;
                overflow: hidden !important;
                overscroll-behavior: none;
            }

            [data-testid="stHeader"] {
                display: none;
            }

            [data-testid="stMainBlockContainer"] {
                display: flex;
                width: 100%;
                max-width: 100%;
                min-height: 100dvh;
                flex-direction: column;
                justify-content: center;
                padding: clamp(0.5rem, 2vw, 1rem) !important;
            }

            [data-testid="stMainBlockContainer"]
            > [data-testid="stVerticalBlock"] {
                min-height: 100%;
                justify-content: center;
            }

            .st-key-auth_card {
                width: min(72rem, calc(100% - 1.5rem));
                max-width: 100%;
                min-height: 38rem;
                max-height: calc(100dvh - 1rem);
                margin-inline: auto;
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 1.5rem;
                background: #111c32;
                box-shadow: 0 1.5rem 4rem rgba(2, 6, 23, 0.42);
            }

            .st-key-auth_card > [data-testid="stVerticalBlock"],
            .st-key-auth_card > [data-testid="stVerticalBlock"] > div,
            .st-key-auth_card [data-testid="stHorizontalBlock"] {
                gap: 0 !important;
                align-items: stretch;
            }

            .st-key-auth_card [data-testid="stColumn"] {
                min-width: 0 !important;
            }

            .st-key-auth_welcome {
                position: relative;
                display: flex;
                min-height: 38rem;
                height: 100%;
                overflow: hidden;
                padding: clamp(2rem, 4vw, 3.5rem);
                background:
                    radial-gradient(circle at 15% 15%, rgba(255,255,255,.18), transparent 22%),
                    radial-gradient(circle at 85% 82%, rgba(34,211,238,.22), transparent 28%),
                    linear-gradient(145deg, #2563eb 0%, #4338ca 52%, #6d28d9 100%);
            }

            .st-key-auth_welcome::after {
                content: "";
                position: absolute;
                right: -5rem;
                bottom: -6rem;
                width: 18rem;
                height: 18rem;
                border: 1px solid rgba(255,255,255,.18);
                border-radius: 50%;
                box-shadow:
                    0 0 0 2.5rem rgba(255,255,255,.035),
                    0 0 0 5rem rgba(255,255,255,.025);
                pointer-events: none;
            }

            .st-key-auth_welcome > [data-testid="stVerticalBlock"] {
                position: relative;
                z-index: 1;
                justify-content: center;
                gap: 0.9rem;
            }

            .st-key-auth_welcome h1,
            .st-key-auth_welcome h3,
            .st-key-auth_welcome p {
                color: #ffffff !important;
            }

            .st-key-auth_welcome h1 {
                max-width: 28rem;
                margin: 0;
                font-size: clamp(2.75rem, 4.5vw, 4.75rem);
                line-height: 1.03;
                letter-spacing: -0.04em;
            }

            .st-key-auth_welcome p {
                max-width: 28rem;
                margin: 0;
                color: rgba(255,255,255,.86) !important;
                font-size: 1.05rem;
                line-height: 1.6;
            }

            .st-key-auth_form {
                min-height: 38rem;
                height: auto;
                max-height: calc(100dvh - 1rem);
                padding: clamp(1.75rem, 3.5vw, 3rem);
                overflow-y: auto;
                scrollbar-width: thin;
                background: #111827;
            }

            .st-key-auth_form > [data-testid="stVerticalBlock"] {
                gap: 0.55rem;
            }

            .st-key-auth_form h2,
            .st-key-auth_form p {
                margin-block: 0;
            }

            .st-key-auth_form h2 {
                font-size: clamp(2rem, 3vw, 2.65rem);
            }

            .st-key-auth_form [data-testid="stTabs"] [role="tablist"] {
                gap: 0.25rem;
            }

            .st-key-auth_form [data-testid="stTabs"] [role="tab"] {
                flex: 1;
                justify-content: center;
                white-space: nowrap;
            }

            .st-key-auth_form [data-testid="stForm"] {
                padding: 0.65rem 0 0.45rem;
                border: 0;
            }

            .st-key-auth_form [data-testid="stForm"]
            > [data-testid="stVerticalBlock"] {
                gap: 0.45rem;
            }

            .st-key-auth_form [data-testid="stTextInput"] label,
            .st-key-auth_form [data-testid="stCheckbox"] label {
                margin-bottom: 0.1rem;
            }

            .st-key-auth_panel {
                width: min(31rem, calc(100% - 0.5rem));
                max-height: calc(100dvh - 1rem);
                margin-inline: auto;
                padding: clamp(1.25rem, 3vw, 2.25rem);
                overflow-y: auto;
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 1.5rem;
                background: #111827;
                box-shadow: 0 1.5rem 4rem rgba(2, 6, 23, 0.42);
            }

            .st-key-auth_panel > [data-testid="stVerticalBlock"] {
                gap: 0.55rem;
            }

            @media (max-width: 760px) {
                [data-testid="stMainBlockContainer"] {
                    justify-content: center;
                    padding:
                        calc(.85rem + env(safe-area-inset-top, 0px))
                        .75rem
                        .85rem !important;
                }

                [data-testid="stMainBlockContainer"]
                > [data-testid="stVerticalBlock"] {
                    justify-content: center;
                }

                .st-key-auth_card {
                    width: min(32rem, calc(100% - 0.25rem));
                    min-height: 0;
                    max-height:
                        calc(100dvh - 1.7rem - env(safe-area-inset-top, 0px));
                    margin-block: auto;
                }

                .st-key-auth_card [data-testid="stHorizontalBlock"]
                > [data-testid="stColumn"]:first-child {
                    display: none;
                }

                .st-key-auth_card [data-testid="stHorizontalBlock"]
                > [data-testid="stColumn"]:last-child {
                    width: 100% !important;
                    flex: 1 1 100% !important;
                }

                .st-key-auth_form {
                    height: auto;
                    min-height: auto;
                    max-height:
                        calc(100dvh - 1.7rem - env(safe-area-inset-top, 0px));
                    padding: 1.25rem;
                }

                .st-key-auth_form [data-testid="stTextInput"] input,
                .st-key-auth_panel [data-testid="stTextInput"] input {
                    font-size: 16px !important;
                }
            }

            @media (max-height: 720px) {
                .st-key-auth_form {
                    padding-top: 1rem;
                    padding-bottom: 1rem;
                }

                .st-key-auth_form > [data-testid="stVerticalBlock"] {
                    gap: 0.35rem;
                }
            }
        </style>
        """
    )


def apply_main_layout() -> None:
    """Harmoniza diálogos e identidade da conta após a autenticação."""
    st.html(
        """
        <style>
            [data-testid="stApp"] {
                --finscope-glass-border: rgba(148, 163, 184, .20);
                --finscope-glass-bg:
                    linear-gradient(145deg, rgba(51, 65, 85, .56), rgba(15, 23, 42, .34)),
                    rgba(15, 23, 42, .36);
                --finscope-glass-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, .08),
                    0 .9rem 2.5rem rgba(2, 6, 23, .16);
            }

            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                overflow-x: clip;
            }

            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 12% 0%, rgba(16, 185, 129, .08), transparent 30rem),
                    radial-gradient(circle at 94% 20%, rgba(59, 130, 246, .10), transparent 36rem),
                    var(--background-color);
            }

            [data-testid="stMainBlockContainer"] {
                width: min(100%, 92rem);
                padding-top: clamp(1.4rem, 3vw, 2.3rem);
                padding-bottom: 3rem;
            }

            [data-testid="stMainBlockContainer"]
            > [data-testid="stVerticalBlock"] {
                gap: 1rem;
            }

            [data-testid="stMain"] h1,
            [data-testid="stMain"] h2,
            [data-testid="stMain"] h3 {
                font-family: ui-rounded, "SF Pro Display", Inter, system-ui, sans-serif;
                letter-spacing: -.035em;
            }

            [data-testid="stMain"] h1 {
                font-size: clamp(2.35rem, 4.7vw, 4rem);
                line-height: 1.04;
            }

            [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stMain"] [data-testid="stMetric"],
            [data-testid="stMain"] [data-testid="stForm"],
            [data-testid="stMain"] [data-testid="stExpander"],
            [data-testid="stMain"] [role="tabpanel"],
            [data-testid="stMain"] [data-testid="stChatMessage"] {
                border: 1px solid var(--finscope-glass-border) !important;
                border-radius: 1.2rem !important;
                background: var(--finscope-glass-bg) !important;
                box-shadow: var(--finscope-glass-shadow);
                -webkit-backdrop-filter: blur(22px) saturate(145%);
                backdrop-filter: blur(22px) saturate(145%);
            }

            [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stMain"] [data-testid="stForm"],
            [data-testid="stMain"] [role="tabpanel"],
            [data-testid="stMain"] [data-testid="stChatMessage"] {
                padding: clamp(1.1rem, 2vw, 1.45rem) !important;
            }

            [data-testid="stMain"] [data-testid="stMetric"] {
                position: relative;
                width: 100%;
                height: 10rem;
                min-height: 10rem;
                padding: 1.15rem 1.3rem 1.1rem !important;
                overflow: hidden;
                transition: transform .24s ease, border-color .24s ease, box-shadow .24s ease;
            }

            [data-testid="stMain"] [data-testid="stMetric"]:hover {
                transform: translateY(-3px);
                border-color: rgba(110, 231, 183, .28) !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.11),
                    0 1.15rem 2.8rem rgba(2, 6, 23, .22);
            }

            [data-testid="stMain"] [data-testid="stMetric"]::before {
                content: "";
                position: absolute;
                inset: 0 auto auto 0;
                width: 72%;
                height: 1px;
                background: linear-gradient(90deg, rgba(255,255,255,.38), transparent);
                pointer-events: none;
            }

            [data-testid="stMain"] [data-testid="stMetricLabel"] {
                margin-bottom: .3rem;
                color: rgba(203, 213, 225, .76);
                font-weight: 650;
            }

            [data-testid="stMain"] [data-testid="stMetricValue"] {
                letter-spacing: -.035em;
            }

            [data-testid="stMain"] [data-testid="stExpander"] details {
                overflow: hidden;
                border-radius: inherit;
            }

            [data-testid="stMain"] [data-testid="stExpander"] summary {
                padding: .9rem 1.15rem;
            }

            [data-testid="stMain"] [data-testid="stExpander"] details > div {
                padding: 0 1.15rem 1.15rem;
            }

            [data-testid="stMain"] [data-testid="stTabs"] [role="tablist"] {
                width: fit-content;
                max-width: 100%;
                padding: .3rem;
                overflow-x: auto;
                border: 1px solid rgba(148, 163, 184, .16);
                border-radius: .95rem;
                background: rgba(15, 23, 42, .28);
                -webkit-backdrop-filter: blur(16px) saturate(135%);
                backdrop-filter: blur(16px) saturate(135%);
            }

            [data-testid="stMain"] [data-testid="stTabs"] [role="tab"] {
                border-radius: .68rem;
            }

            [data-testid="stMain"] [role="tabpanel"] {
                margin-top: .75rem;
            }

            [data-testid="stMain"] [data-testid="stDataFrame"],
            [data-testid="stMain"] [data-testid="stVegaLiteChart"] {
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, .16);
                border-radius: 1rem;
                background: rgba(15, 23, 42, .18);
            }

            [data-testid="stMain"] [data-testid="stAlert"] {
                border-radius: 1rem;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.05);
                -webkit-backdrop-filter: blur(14px) saturate(130%);
                backdrop-filter: blur(14px) saturate(130%);
            }

            [data-testid="stMain"] .stButton > button,
            [data-testid="stMain"] .stDownloadButton > button,
            [data-testid="stMain"] .stLinkButton > a {
                min-height: 2.7rem;
                border-radius: .82rem;
            }

            div[role="dialog"] {
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, .22) !important;
                border-radius: 1.45rem !important;
                background:
                    linear-gradient(145deg, rgba(30, 41, 59, .82), rgba(15, 23, 42, .68)),
                    rgba(15, 23, 42, .72) !important;
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, .10),
                    0 1.7rem 5rem rgba(2, 6, 23, .48) !important;
                -webkit-backdrop-filter: blur(30px) saturate(150%);
                backdrop-filter: blur(30px) saturate(150%);
            }

            div[role="dialog"] [data-testid="stForm"] {
                border-color: rgba(148, 163, 184, .18);
                border-radius: 1rem;
                background: rgba(15, 23, 42, .20);
            }

            div[role="dialog"] [data-testid="stTextArea"] textarea,
            div[role="dialog"] [data-testid="stTextInput"] input {
                border-color: rgba(148, 163, 184, .24);
                background: rgba(15, 23, 42, .42);
            }

            .finscope-user-card {
                margin: .35rem 0 .9rem;
                padding: .9rem 1rem;
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, .18);
                border-radius: 1rem;
                background:
                    linear-gradient(135deg, rgba(16, 185, 129, .11), rgba(30, 41, 59, .34)),
                    rgba(15, 23, 42, .28);
                box-shadow: inset 0 1px 0 rgba(255,255,255,.07);
                -webkit-backdrop-filter: blur(18px) saturate(140%);
                backdrop-filter: blur(18px) saturate(140%);
            }

            .finscope-user-label {
                display: block;
                margin-bottom: .18rem;
                color: rgba(203, 213, 225, .68);
                font-size: .72rem;
                font-weight: 650;
                letter-spacing: .07em;
                text-transform: uppercase;
            }

            .finscope-user-name {
                display: block;
                overflow-wrap: anywhere;
                background: linear-gradient(105deg, #047857 0%, #10b981 48%, #86efac 100%);
                background-clip: text;
                -webkit-background-clip: text;
                color: transparent;
                -webkit-text-fill-color: transparent;
                font-family: ui-rounded, "SF Pro Display", Inter, system-ui, sans-serif;
                font-size: clamp(1.15rem, 1.8vw, 1.45rem);
                font-weight: 780;
                line-height: 1.18;
                letter-spacing: -.025em;
            }

            @media (max-width: 880px) {
                [data-testid="stMainBlockContainer"] {
                    padding-inline: 1rem;
                    padding-top:
                        calc(4.1rem + env(safe-area-inset-top, 0px)) !important;
                }

                [data-testid="stMain"] input,
                [data-testid="stMain"] textarea,
                [data-testid="stMain"] select {
                    font-size: 16px !important;
                }

                [data-testid="stMain"] [data-testid="stMetric"] {
                    height: 8.7rem;
                    min-height: 8.7rem;
                    padding: 1rem 1.1rem !important;
                }

                [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
                [data-testid="stMain"] [data-testid="stForm"],
                [data-testid="stMain"] [role="tabpanel"],
                [data-testid="stMain"] [data-testid="stChatMessage"] {
                    padding: 1rem !important;
                }
            }

            @media (max-width: 760px) {
                [data-testid="stMainBlockContainer"]
                > [data-testid="stVerticalBlock"] {
                    gap: .8rem;
                }

                [data-testid="stMain"] h1 {
                    margin-bottom: .25rem;
                    font-size: clamp(2rem, 8vw, 2.75rem);
                    line-height: 1.04;
                }

                [data-testid="stMain"]
                [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
                    display: grid !important;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: .65rem !important;
                    align-items: stretch !important;
                }

                [data-testid="stMain"]
                [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])
                > [data-testid="stColumn"] {
                    width: 100% !important;
                    min-width: 0 !important;
                    flex: none !important;
                }

                [data-testid="stMain"] [data-testid="stMetric"] {
                    height: 7.2rem;
                    min-height: 7.2rem;
                    padding: .82rem .9rem .75rem !important;
                    border-radius: 1rem !important;
                }

                [data-testid="stMain"] [data-testid="stMetricLabel"] {
                    min-height: 1.85rem;
                    margin-bottom: .08rem;
                    font-size: .74rem;
                    line-height: 1.25;
                }

                [data-testid="stMain"] [data-testid="stMetricValue"] {
                    font-size: clamp(1.22rem, 5.2vw, 1.7rem);
                    line-height: 1.08;
                }

                [data-testid="stMain"] [data-testid="stMetricDelta"] {
                    font-size: .69rem;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                [data-testid="stMain"] [data-testid="stMetric"] {
                    transition: none !important;
                }

                [data-testid="stMain"] [data-testid="stMetric"]:hover {
                    transform: none !important;
                }
            }
        </style>
        """
    )


def show_delivery(result: DeliveryResult) -> None:
    """Exibe o resultado seguro do envio de um e-mail de recuperação."""
    if result.sent:
        st.success(result.message, icon=":material/mark_email_read:")
    elif result.debug_link:
        st.info(result.message, icon=":material/developer_mode:")
        st.link_button(
            "Abrir link de teste",
            result.debug_link,
            icon=":material/open_in_new:",
            width="stretch",
        )
        st.caption("No Docker local, os e-mails também aparecem em http://localhost:8025.")
    else:
        st.warning(result.message, icon=":material/schedule:")


def initialize_database_or_stop() -> None:
    """Inicializa o banco ou apresenta uma falha segura de infraestrutura."""
    try:
        init_db()
    except OperationalError:
        apply_auth_layout()
        with st.container(key="auth_panel", horizontal_alignment="center"):
            st.title(
                "Banco de dados indisponível",
                text_alignment="center",
            )
            st.error(
                "O FinScope não conseguiu se conectar ao PostgreSQL.",
                icon=":material/database_off:",
            )
            st.write(
                "Reinicie os serviços pelo Docker. A configuração atual "
                "prepara o papel restrito e aplica as políticas RLS antes de "
                "iniciar o aplicativo."
            )
            st.code("docker compose up --build -d", language="powershell")
            st.caption(
                "Se o problema continuar, consulte os registros com "
                "`docker compose logs --tail=50 database_password_sync "
                "database_migrate app`."
            )
        st.stop()


@st.dialog("Recuperar senha", icon=":material/lock_reset:")
def forgot_password() -> None:
    """Solicita um link de redefinição sem revelar se a conta existe."""
    st.write(
        "Informe o e-mail cadastrado. O link expira em 30 minutos e pode ser "
        "utilizado uma única vez."
    )
    with st.form("forgot_password_form"):
        email = st.text_input("E-mail", placeholder="voce@exemplo.com", key="forgot_email")
        submitted = st.form_submit_button(
            "Enviar link",
            type="primary",
            icon=":material/send:",
            width="stretch",
        )
    if submitted:
        # A resposta não revela se o e-mail está cadastrado.
        result = send_password_reset_email(email)
        if result.debug_link:
            show_delivery(result)
        else:
            st.success(
                "Se existir uma conta com esse e-mail, enviaremos as instruções.",
                icon=":material/mark_email_read:",
            )


def reset_password_screen(raw_token: str) -> None:
    """Apresenta o formulário para cadastrar uma nova senha."""
    apply_auth_layout()
    with st.container(key="auth_panel", horizontal_alignment="center"):
        st.title("Criar nova senha", text_alignment="center")
        st.caption(
            "Use ao menos 10 caracteres, com maiúscula, minúscula e número.",
            text_alignment="center",
        )
        with st.form("reset_password_form"):
            password = st.text_input("Nova senha", type="password")
            confirmation = st.text_input("Confirme a nova senha", type="password")
            submitted = st.form_submit_button(
                "Alterar senha",
                type="primary",
                icon=":material/lock_reset:",
                width="stretch",
            )
        if submitted:
            if password != confirmation:
                st.error("As senhas não coincidem.")
            else:
                ok, message = reset_password_token(raw_token, password)
                if ok:
                    st.session_state.flash = ("success", message)
                    st.query_params.clear()
                    st.rerun()
                st.error(message, icon=":material/error:")
        if st.button("Voltar ao login", icon=":material/arrow_back:", width="stretch"):
            st.query_params.clear()
            st.rerun()


def login_screen() -> None:
    """Apresenta login e cadastro em um cartão dividido e responsivo."""
    apply_auth_layout()
    with st.container(key="auth_card"):
        welcome_column, form_column = st.columns([1.08, 1], gap=None)
        with welcome_column:
            with st.container(key="auth_welcome"):
                st.markdown("### :material/account_balance_wallet: FinScope")
                st.title("Bem-vindo(a)!")
                st.write(
                    "Este é o seu aplicativo de finanças, feito para organizar "
                    "sua rotina e seus investimentos!"
                )
                with st.container(horizontal=True):
                    st.badge(
                        "Finanças pessoais",
                        icon=":material/receipt_long:",
                        color="blue",
                    )
                    st.badge(
                        "Investimentos",
                        icon=":material/trending_up:",
                        color="green",
                    )
                st.caption("Beta fechada para até 10 participantes.")
        with form_column:
            with st.container(key="auth_form"):
                st.markdown("## Acesse sua conta")
                st.caption("Entre ou crie uma conta para continuar.")
                flash = st.session_state.pop("flash", None)
                if flash:
                    (st.success if flash[0] == "success" else st.error)(flash[1])
                enter, signup = st.tabs(
                    [":material/login: Entrar", ":material/person_add: Criar conta"]
                )
                with enter:
                    with st.form("login_form"):
                        email = st.text_input(
                            "E-mail",
                            placeholder="voce@exemplo.com",
                            key="login_email",
                        )
                        password = st.text_input(
                            "Senha",
                            type="password",
                            key="login_password",
                        )
                        submitted = st.form_submit_button(
                            "Entrar",
                            type="primary",
                            icon=":material/login:",
                            width="stretch",
                        )
                    if submitted:
                        user = authenticate(email, password)
                        if user:
                            st.session_state.user = user
                            st.session_state.help_messages = []
                            st.rerun()
                        st.error("E-mail ou senha incorretos.", icon=":material/error:")
                    if st.button(
                        "Esqueceu sua senha?",
                        icon=":material/lock_reset:",
                        width="stretch",
                    ):
                        forgot_password()
                    st.caption(
                        "Primeiro acesso? Selecione **Criar conta** acima."
                    )
                with signup:
                    with st.form("signup_form"):
                        name = st.text_input(
                            "Como podemos chamar você?",
                            placeholder="Seu nome",
                        )
                        new_email = st.text_input(
                            "E-mail",
                            placeholder="voce@exemplo.com",
                            key="signup_email",
                        )
                        invite_code = st.text_input(
                            "Código de convite",
                            type="password",
                            help="Solicite o código ao responsável pela beta.",
                            key="signup_invite_code",
                        )
                        new_password = st.text_input(
                            "Crie uma senha",
                            type="password",
                            help=(
                                "Use 10 ou mais caracteres, com maiúscula, "
                                "minúscula e número."
                            ),
                        )
                        confirm = st.text_input(
                            "Confirme a senha",
                            type="password",
                        )
                        agreed = st.checkbox(
                            "Concordo em participar da beta e usar a plataforma "
                            "para fins educacionais."
                        )
                        created = st.form_submit_button(
                            "Criar minha conta",
                            type="primary",
                            icon=":material/person_add:",
                            width="stretch",
                        )
                    if created:
                        if new_password != confirm:
                            st.error("As senhas não coincidem.")
                        elif not agreed:
                            st.warning("Confirme que está de acordo para continuar.")
                        else:
                            ok, message = create_user(
                                name,
                                new_email,
                                new_password,
                                invite_code,
                            )
                            if ok:
                                st.session_state.flash = ("success", message)
                                st.rerun()
                            else:
                                st.error(message)


@st.dialog("Enviar feedback", icon=":material/rate_review:")
def feedback_dialog() -> None:
    """Envia um comentário da pessoa autenticada diretamente por e-mail."""
    st.write(
        "Descreva o problema, a sugestão ou a sua experiência. O comentário será "
        "encaminhado diretamente ao responsável pela beta."
    )
    with st.form("beta_feedback_form"):
        message = st.text_area(
            "Comentário",
            placeholder="Conte o que aconteceu ou o que poderia melhorar...",
            max_chars=2_000,
            height=220,
        )
        submitted = st.form_submit_button(
            "Enviar feedback",
            type="primary",
            icon=":material/send:",
            width="stretch",
        )
    if submitted:
        try:
            result = send_feedback_email(
                st.session_state.user["email"],
                st.session_state.user["name"],
                message,
            )
            if result.sent:
                st.success(
                    "Obrigado! Seu comentário foi enviado.",
                    icon=":material/check_circle:",
                )
            else:
                st.warning(result.message, icon=":material/schedule:")
        except ValueError as error:
            st.error(str(error))

initialize_database_or_stop()

reset = st.query_params.get("reset")
if reset:
    reset_password_screen(reset)
    st.stop()

if not st.session_state.user:
    login_screen()
    st.stop()

stored_user = st.session_state.user
user = authenticated_user(stored_user.get("id")) if isinstance(stored_user, dict) else None
if not user:
    st.session_state.clear()
    st.warning("Sua sessão não é mais válida. Entre novamente.")
    st.rerun()
st.session_state.user = user
apply_main_layout()
mobile_navigation_gesture(key="mobile_navigation_gesture")
with st.sidebar:
    st.markdown("### :material/account_balance_wallet: FinScope")
    safe_user_name = escape(str(user["name"]))
    st.html(
        f"""
        <div class="finscope-user-card">
            <span class="finscope-user-label">Conectado como</span>
            <strong class="finscope-user-name">{safe_user_name}</strong>
        </div>
        """
    )
    st.badge("Beta 5.2", icon=":material/science:", color="blue")
    if st.button("Enviar feedback", icon=":material/rate_review:", width="stretch"):
        feedback_dialog()
    if st.button("Sair da conta", icon=":material/logout:", width="stretch"):
        st.session_state.user = None
        st.session_state.help_messages = []
        st.rerun()
    st.caption("Seus dados são separados por conta.")

dashboard_title = "Minha dashboard" if get_dashboard(user["id"]) else "Criar minha dashboard"

home_page = st.Page("app_pages/home.py", title="Início", icon=":material/home:")
dashboard_page = st.Page(
    "app_pages/dashboard.py", title=dashboard_title, icon=":material/dashboard:"
)
finance_page = st.Page(
    "app_pages/personal_finance.py",
    title="Finanças pessoais",
    icon=":material/account_balance_wallet:",
)
planning_page = st.Page(
    "app_pages/planning.py", title="Planejamento", icon=":material/event_note:"
)
investments_page = st.Page(
    "app_pages/investments.py", title="Investimentos", icon=":material/query_stats:"
)
help_page = st.Page(
    "app_pages/assistant.py", title="Ajuda", icon=":material/help_center:"
)
settings_page = st.Page(
    "app_pages/settings.py", title="Minha conta", icon=":material/manage_accounts:"
)
pages = {
    "": [home_page, dashboard_page, investments_page],
    "Organizar": [finance_page, planning_page],
    "Suporte": [help_page, settings_page],
}
page = st.navigation(pages, position="top")
page.run()

