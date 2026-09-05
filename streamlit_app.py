"""Ponto de entrada, autenticação e navegação do Revo Beta 5.2.

A versão atual mantém a recuperação de senha por e-mail, mas não exige a
verificação do endereço eletrônico para permitir o acesso. A estrutura de
verificação permanece isolada na camada de serviços para uma versão futura.
"""

from html import escape

import streamlit as st
from sqlalchemy.exc import OperationalError

from utils.database import (
    DatabaseSecurityError,
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
from utils.ui import inject_app_styles

st.set_page_config(
    page_title="Revo",
    page_icon="static/revo-logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
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
    let sidebarWasOpen = false;

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

    const findSidebarCloseButton = () => document.querySelector(
        '[data-testid="stSidebarCollapseButton"] button, '
        + '[data-testid="stSidebar"] button[aria-label*="Close" i], '
        + '[data-testid="stSidebar"] button[aria-label*="Fechar" i]'
    );

    const isSidebarOpen = () => {
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return false;
        const style = window.getComputedStyle(sidebar);
        return style.display !== "none" && sidebar.getBoundingClientRect().width > 40;
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
        sidebarWasOpen = isSidebarOpen();
        tracking = sidebarWasOpen || touch.clientX <= 84;
    };

    const onTouchEnd = (event) => {
        if (!tracking || event.changedTouches.length !== 1) return;
        tracking = false;
        const touch = event.changedTouches[0];
        const horizontalDistance = touch.clientX - startX;
        const verticalDistance = Math.abs(touch.clientY - startY);
        const duration = performance.now() - startedAt;

        if (!sidebarWasOpen && horizontalDistance >= 72 && verticalDistance <= 56 && duration <= 800) {
            findSidebarButton()?.click();
        } else if (sidebarWasOpen && horizontalDistance <= -72 && verticalDistance <= 56 && duration <= 800) {
            findSidebarCloseButton()?.click();
        }
    };

    const onTouchCancel = () => {
        tracking = false;
    };

    const onSidebarNavigation = (event) => {
        if (!isMobile()) return;
        const link = event.target?.closest(
            '[data-testid="stSidebarNav"] a, [data-testid="stSidebar"] a'
        );
        if (!link) return;
        window.setTimeout(() => {
            window.scrollTo({ top: 0, left: 0, behavior: "auto" });
            document.querySelector('[data-testid="stAppViewContainer"]')?.scrollTo({
                top: 0, left: 0, behavior: "auto"
            });
        }, 40);
        window.setTimeout(() => findSidebarCloseButton()?.click(), 120);
    };

    let initialCloseAttempts = 0;
    const initialCloseTimer = window.setInterval(() => {
        initialCloseAttempts += 1;
        if (isMobile() && isSidebarOpen()) {
            findSidebarCloseButton()?.click();
            window.clearInterval(initialCloseTimer);
        } else if (!isMobile() || initialCloseAttempts >= 12) {
            window.clearInterval(initialCloseTimer);
        }
    }, 140);

    document.addEventListener("touchstart", onTouchStart, { passive: true });
    document.addEventListener("touchend", onTouchEnd, { passive: true });
    document.addEventListener("touchcancel", onTouchCancel, { passive: true });
    document.addEventListener("click", onSidebarNavigation, true);

    return () => {
        window.clearInterval(initialCloseTimer);
        document.removeEventListener("touchstart", onTouchStart);
        document.removeEventListener("touchend", onTouchEnd);
        document.removeEventListener("touchcancel", onTouchCancel);
        document.removeEventListener("click", onSidebarNavigation, true);
    };
}
"""

mobile_navigation_gesture = st.components.v2.component(
    "revo_mobile_navigation_gesture",
    js=MOBILE_NAVIGATION_JS,
)

THEME_SYNC_JS = r"""
export default function(component) {
    const { data } = component;
    const root = component.parentElement instanceof ShadowRoot
        ? component.parentElement.host
        : component.parentElement;
    const wrapper = root?.closest('[data-testid="stElementContainer"]');
    if (wrapper) wrapper.style.display = "none";

    const desired = data?.light ? "Light" : "Dark";
    const desiredType = desired.toLowerCase();
    const paths = new Set([window.location.pathname, ...(data?.paths || [])]);

    for (const pathname of paths) {
        const normalized = pathname === "" ? "/" : pathname;
        const key = `stActiveTheme-${normalized}-v2`;
        const next = JSON.stringify(desired);
        if (window.localStorage.getItem(key) !== next) {
            window.localStorage.setItem(key, next);
        }
    }

    if (data?.current && data.current !== desiredType) {
        const chooseTheme = (attempt = 0) => {
            const menuButton = document.querySelector('[data-testid="stMainMenuButton"]');
            if (!menuButton) {
                if (attempt < 12) window.setTimeout(() => chooseTheme(attempt + 1), 60);
                return;
            }

            if (menuButton.getAttribute("aria-expanded") !== "true") {
                menuButton.click();
            }

            window.setTimeout(() => {
                const choices = Array.from(document.querySelectorAll('[role="menuitemradio"]'));
                const target = choices.find((choice) =>
                    (choice.textContent || "").trim().toLowerCase().endsWith(desiredType)
                );
                if (target) {
                    target.click();
                    window.setTimeout(() => {
                        if (menuButton.getAttribute("aria-expanded") === "true") {
                            menuButton.click();
                        }
                    }, 90);
                } else if (attempt < 12) {
                    chooseTheme(attempt + 1);
                }
            }, 35);
        };
        chooseTheme();
    }
}
"""

sync_browser_theme = st.components.v2.component(
    "revo_browser_theme_sync",
    js=THEME_SYNC_JS,
)

st.session_state.setdefault("user", None)
st.session_state.setdefault("help_messages", [])
st.session_state.setdefault("help_pending_prompt", None)
st.session_state.setdefault("flash", None)
try:
    initial_light_theme = st.context.theme.type == "light"
except (AttributeError, RuntimeError):
    initial_light_theme = False
st.session_state.setdefault("theme_light", initial_light_theme)


def apply_auth_layout() -> None:
    """Aplica o sistema visual responsivo das telas públicas de autenticação."""
    light_theme = bool(st.session_state.get("theme_light", False))
    palette = {
        "canvas": "#EEF3F9" if light_theme else "#050B16",
        "surface": "#FFFFFF" if light_theme else "#0B1628",
        "surface_soft": "#F6F8FC" if light_theme else "#101D31",
        "input": "#F8FAFD" if light_theme else "#0D1A2D",
        "text": "#122033" if light_theme else "#F5F8FC",
        "muted": "#607089" if light_theme else "#9AACBF",
        "border": "#D7E0EB" if light_theme else "#263750",
        "shadow": "rgba(37, 54, 82, .18)" if light_theme else "rgba(0, 0, 0, .46)",
    }
    st.html(
        f"""
        <style>
            [data-testid="stApp"] {{
                --auth-canvas: {palette["canvas"]};
                --auth-surface: {palette["surface"]};
                --auth-surface-soft: {palette["surface_soft"]};
                --auth-input: {palette["input"]};
                --auth-text: {palette["text"]};
                --auth-muted: {palette["muted"]};
                --auth-border: {palette["border"]};
                --auth-shadow: {palette["shadow"]};
                --auth-blue: #366DEF;
                --auth-blue-strong: #2459D5;
                --auth-green: #22C58B;
                --auth-radius: 22px;
            }}
        </style>
        """
        + r"""
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

            [data-testid="stApp"],
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                background: var(--auth-canvas) !important;
                color: var(--auth-text) !important;
                transition: background-color 180ms ease, color 180ms ease;
            }

            [data-testid="stHeader"] {
                display: none;
            }

            [data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarNav"],
            [data-testid="stNavigation"] {
                display: none !important;
                visibility: hidden !important;
            }

            [data-testid="stMainBlockContainer"] {
                display: flex;
                width: 100%;
                max-width: 100%;
                min-height: 100dvh;
                flex-direction: column;
                justify-content: center;
                padding: clamp(1rem, 3vw, 2.5rem) !important;
            }

            [data-testid="stMainBlockContainer"]
            > [data-testid="stVerticalBlock"] {
                min-height: 100%;
                justify-content: center;
            }

            .st-key-auth_card {
                width: min(74rem, calc(100% - 1rem));
                max-width: 100%;
                height: min(46rem, calc(100dvh - 2rem)) !important;
                min-height: min(38rem, calc(100dvh - 2rem)) !important;
                margin-inline: auto;
                overflow: hidden;
                border: 1px solid var(--auth-border);
                border-radius: var(--auth-radius);
                background: var(--auth-surface);
                box-shadow: 0 1.75rem 5.5rem var(--auth-shadow);
                animation: auth-card-in .62s cubic-bezier(.2,.78,.2,1) both;
            }

            .st-key-auth_card > [data-testid="stVerticalBlock"],
            .st-key-auth_card > [data-testid="stVerticalBlock"] > div,
            .st-key-auth_card [data-testid="stHorizontalBlock"] {
                gap: 0 !important;
                align-items: stretch;
                height: 100%;
            }

            .st-key-auth_card [data-testid="stColumn"] {
                min-width: 0 !important;
            }

            .st-key-auth_card [data-testid="stColumn"]
            > [data-testid="stVerticalBlock"]
            > [data-testid="stLayoutWrapper"] {
                height: 100%;
            }

            .st-key-auth_welcome {
                position: relative;
                display: flex;
                min-height: 100%;
                height: 100%;
                overflow: hidden;
                padding: clamp(2rem, 4vw, 3.5rem);
                background-image:
                    linear-gradient(180deg, rgba(3, 10, 26, .18), rgba(2, 8, 20, .74)),
                    url("app/static/revo-auth-visual.png");
                background-position: center;
                background-size: cover;
            }

            .st-key-auth_welcome > [data-testid="stVerticalBlock"] {
                position: relative;
                z-index: 1;
                justify-content: space-between;
                gap: 1.2rem;
            }

            .st-key-auth_welcome h1,
            .st-key-auth_welcome h3,
            .st-key-auth_welcome p {
                color: #ffffff !important;
            }

            .st-key-auth_welcome h1 {
                max-width: 25rem;
                margin: 0;
                font-size: clamp(2.4rem, 4vw, 4rem);
                line-height: 1.02;
                letter-spacing: -0.04em;
            }

            .auth-brand {
                display: inline-flex;
                width: fit-content;
                align-items: center;
                gap: .7rem;
                color: #ffffff;
                font-family: Manrope, Inter, sans-serif;
                font-size: 1.22rem;
                font-weight: 780;
                letter-spacing: -.03em;
            }

            .auth-brand img {
                width: 2.45rem;
                height: 2.45rem;
                object-fit: contain;
                filter: drop-shadow(0 .45rem 1.1rem rgba(15, 118, 255, .24));
            }

            .st-key-auth_welcome p {
                max-width: 25rem;
                margin: 0;
                color: rgba(255,255,255,.86) !important;
                font-size: 1rem;
                line-height: 1.55;
            }

            .auth-kicker {
                width: fit-content;
                padding: .38rem .68rem;
                border: 1px solid rgba(255,255,255,.24);
                border-radius: 999px;
                background: rgba(5, 15, 37, .36);
                color: rgba(255,255,255,.9);
                font-size: .71rem;
                font-weight: 750;
                letter-spacing: .09em;
                text-transform: uppercase;
                backdrop-filter: blur(14px);
            }

            .st-key-auth_story > [data-testid="stVerticalBlock"] {
                gap: .8rem;
            }

            .st-key-auth_steps {
                max-width: 24rem;
                padding: .8rem;
                border: 1px solid rgba(255,255,255,.18);
                border-radius: 15px;
                background: rgba(4, 12, 30, .44);
                backdrop-filter: blur(18px) saturate(125%);
            }

            .st-key-auth_steps > [data-testid="stVerticalBlock"] {
                gap: .22rem;
            }

            .st-key-auth_steps [data-testid="stCaptionContainer"] p {
                color: rgba(255,255,255,.66) !important;
                font-size: .7rem;
                font-weight: 700;
                letter-spacing: .08em;
                text-transform: uppercase;
            }

            .st-key-auth_steps [data-testid="stMarkdownContainer"] p {
                margin: 0;
                padding: .58rem .7rem;
                border-radius: 9px;
                color: rgba(255,255,255,.78) !important;
                font-size: .84rem;
            }

            .st-key-auth_steps [data-testid="stMarkdownContainer"] strong {
                color: #ffffff !important;
            }

            .st-key-auth_form {
                min-height: 100%;
                height: 100%;
                padding: clamp(1.8rem, 4vw, 3.6rem);
                overflow-y: auto;
                scrollbar-width: thin;
                background: var(--auth-surface);
                color: var(--auth-text);
            }

            .st-key-auth_form > [data-testid="stVerticalBlock"] {
                min-height: 100%;
                justify-content: center;
                gap: 0.65rem;
            }

            .st-key-auth_form h1,
            .st-key-auth_form h2,
            .st-key-auth_form h3,
            .st-key-auth_form p,
            .st-key-auth_form label,
            .st-key-auth_panel h1,
            .st-key-auth_panel h2,
            .st-key-auth_panel p,
            .st-key-auth_panel label {
                color: var(--auth-text) !important;
            }

            .st-key-auth_form h2,
            .st-key-auth_form p,
            .st-key-auth_panel p {
                margin-block: 0;
            }

            .st-key-auth_form h2 {
                font-size: clamp(2rem, 3.2vw, 2.8rem);
                line-height: 1.06;
                letter-spacing: -.04em;
            }

            .st-key-auth_form [data-testid="stCaptionContainer"] p,
            .st-key-auth_panel [data-testid="stCaptionContainer"] p {
                color: var(--auth-muted) !important;
            }

            .st-key-auth_toolbar > [data-testid="stHorizontalBlock"] {
                align-items: center;
                justify-content: flex-end;
            }

            .st-key-theme_light {
                width: fit-content;
                margin-left: auto;
            }

            .st-key-theme_light label p {
                color: var(--auth-muted) !important;
                font-size: .78rem;
                font-weight: 650;
            }

            .st-key-auth_mode [data-testid="stSegmentedControl"] {
                width: 100%;
            }

            .st-key-auth_mode [role="radiogroup"] {
                width: 100%;
                padding: .28rem;
                border: 1px solid var(--auth-border);
                border-radius: 11px;
                background: var(--auth-surface-soft);
            }

            .st-key-auth_mode [role="radio"] {
                flex: 1 1 50%;
                justify-content: center;
                min-height: 2.45rem;
                border: 0 !important;
                border-radius: 8px !important;
                color: var(--auth-muted) !important;
            }

            .st-key-auth_mode [role="radio"][aria-checked="true"] {
                background: var(--auth-surface) !important;
                color: var(--auth-blue) !important;
                box-shadow: 0 5px 14px var(--auth-shadow);
            }

            .st-key-auth_form [data-testid="stForm"] {
                padding: 0.45rem 0 0.2rem;
                border: 0;
                background: transparent !important;
            }

            .st-key-auth_form [data-testid="stForm"]
            > [data-testid="stVerticalBlock"] {
                gap: 0.55rem;
            }

            .st-key-auth_form [data-testid="stTextInput"] label,
            .st-key-auth_form [data-testid="stCheckbox"] label {
                margin-bottom: 0.1rem;
            }

            .st-key-auth_form [data-baseweb="input"],
            .st-key-auth_panel [data-baseweb="input"] {
                min-height: 2.85rem;
                border-color: var(--auth-border) !important;
                border-radius: 9px !important;
                background: var(--auth-input) !important;
                box-shadow: none !important;
            }

            .st-key-auth_form input,
            .st-key-auth_panel input {
                color: var(--auth-text) !important;
                caret-color: var(--auth-blue) !important;
            }

            .st-key-auth_form input::placeholder,
            .st-key-auth_panel input::placeholder {
                color: var(--auth-muted) !important;
                opacity: .72;
            }

            .st-key-auth_form [data-baseweb="input"]:focus-within,
            .st-key-auth_panel [data-baseweb="input"]:focus-within {
                border-color: var(--auth-blue) !important;
                box-shadow: 0 0 0 3px rgba(54,109,239,.14) !important;
            }

            .st-key-auth_form .stButton button,
            .st-key-auth_form [data-testid="stFormSubmitButton"] button,
            .st-key-auth_panel .stButton button,
            .st-key-auth_panel [data-testid="stFormSubmitButton"] button {
                min-height: 2.85rem;
                border-radius: 9px !important;
                font-weight: 700;
                transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
            }

            .st-key-auth_form [data-testid="stFormSubmitButton"] button,
            .st-key-auth_panel [data-testid="stFormSubmitButton"] button {
                border-color: var(--auth-blue) !important;
                background: var(--auth-blue) !important;
                color: #ffffff !important;
                box-shadow: 0 10px 24px rgba(54,109,239,.22);
            }

            .st-key-auth_form [data-testid="stFormSubmitButton"] button p,
            .st-key-auth_panel [data-testid="stFormSubmitButton"] button p {
                color: #ffffff !important;
            }

            .st-key-auth_form .stButton button:hover,
            .st-key-auth_form [data-testid="stFormSubmitButton"] button:hover,
            .st-key-auth_panel .stButton button:hover,
            .st-key-auth_panel [data-testid="stFormSubmitButton"] button:hover {
                transform: translateY(-1px);
            }

            .st-key-auth_forgot button {
                border-color: transparent !important;
                background: transparent !important;
                color: var(--auth-blue) !important;
                box-shadow: none !important;
            }

            .st-key-auth_forgot button:hover {
                border-color: var(--auth-border) !important;
                background: var(--auth-surface-soft) !important;
            }

            .st-key-auth_form [data-testid="stAlert"],
            .st-key-auth_panel [data-testid="stAlert"] {
                border-radius: 9px !important;
            }

            .st-key-auth_panel {
                width: min(34rem, calc(100% - 1rem));
                max-height: calc(100dvh - 2rem);
                margin-inline: auto;
                padding: clamp(1.25rem, 3vw, 2.25rem);
                overflow-y: auto;
                border: 1px solid var(--auth-border);
                border-radius: var(--auth-radius);
                background: var(--auth-surface);
                box-shadow: 0 1.75rem 5.5rem var(--auth-shadow);
            }

            .st-key-auth_panel > [data-testid="stVerticalBlock"] {
                gap: 0.55rem;
            }

            [role="dialog"] {
                border-color: var(--auth-border) !important;
                background: var(--auth-surface) !important;
                color: var(--auth-text) !important;
            }

            [role="dialog"] h1,
            [role="dialog"] h2,
            [role="dialog"] h3,
            [role="dialog"] p,
            [role="dialog"] label {
                color: var(--auth-text) !important;
            }

            @keyframes auth-card-in {
                from { opacity: 0; transform: translateY(18px) scale(.985); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }

            @media (max-width: 820px) {
                [data-testid="stMainBlockContainer"] {
                    justify-content: center;
                    padding:
                        calc(.65rem + env(safe-area-inset-top, 0px))
                        .75rem
                        calc(.65rem + env(safe-area-inset-bottom, 0px)) !important;
                }

                [data-testid="stMainBlockContainer"]
                > [data-testid="stVerticalBlock"] {
                    justify-content: center;
                }

                .st-key-auth_card {
                    width: min(100%, 35rem);
                    min-height: 0;
                    height: auto;
                    max-height: calc(100dvh - 1.3rem - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px));
                    margin-block: auto;
                    overflow-y: auto;
                }

                .st-key-auth_card [data-testid="stHorizontalBlock"]:has(.st-key-auth_form) {
                    display: block !important;
                    height: auto;
                }

                .st-key-auth_card [data-testid="stColumn"]:has(.st-key-auth_welcome),
                .st-key-auth_card [data-testid="stColumn"]:has(.st-key-auth_form) {
                    width: 100% !important;
                    max-width: none !important;
                    min-width: 0 !important;
                    flex: 1 1 100% !important;
                }

                .st-key-auth_welcome {
                    min-height: 7.7rem;
                    height: 7.7rem;
                    padding: 1.15rem 1.25rem;
                    background-position: 50% 35%;
                }

                .st-key-auth_welcome > [data-testid="stVerticalBlock"] {
                    justify-content: center;
                }

                .st-key-auth_story,
                .st-key-auth_steps {
                    display: none !important;
                }

                .st-key-auth_welcome h3 {
                    margin: 0;
                    font-size: 1.16rem;
                }

                .st-key-auth_form {
                    height: auto !important;
                    min-height: auto;
                    overflow: visible;
                    padding: 1.25rem 1.2rem 1.4rem;
                }

                .st-key-auth_form [data-testid="stTextInput"] input,
                .st-key-auth_panel [data-testid="stTextInput"] input {
                    font-size: 16px !important;
                }

                .st-key-auth_form h2 {
                    font-size: clamp(1.8rem, 8vw, 2.25rem);
                }

                .st-key-auth_form [data-testid="stHorizontalBlock"]:has(.st-key-signup_email) {
                    display: block !important;
                }

                .st-key-auth_form [data-testid="stHorizontalBlock"]:has(.st-key-signup_email)
                > [data-testid="stColumn"] {
                    width: 100% !important;
                    max-width: none !important;
                    min-width: 0 !important;
                    margin-bottom: .45rem;
                }

                .st-key-auth_mode [role="radio"] {
                    min-height: 2.35rem;
                }
            }

            @media (max-height: 720px) {
                .st-key-auth_card {
                    height: calc(100dvh - 1rem) !important;
                }

                .st-key-auth_welcome {
                    padding-block: 1.6rem;
                }

                .st-key-auth_form {
                    padding-top: 1rem;
                    padding-bottom: 1rem;
                }

                .st-key-auth_form > [data-testid="stVerticalBlock"] {
                    gap: 0.35rem;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                .st-key-auth_card,
                .st-key-auth_form .stButton button,
                .st-key-auth_form [data-testid="stFormSubmitButton"] button {
                    animation: none !important;
                    transition: none !important;
                }
            }
        </style>
        """
    )


def apply_main_layout() -> None:
    """Harmoniza diálogos e identidade da conta após a autenticação."""
    inject_app_styles()
    return
    st.html(
        """
        <style>
            [data-testid="stApp"] {
                --revo-glass-border: rgba(148, 163, 184, .20);
                --revo-glass-bg:
                    linear-gradient(145deg, rgba(51, 65, 85, .56), rgba(15, 23, 42, .34)),
                    rgba(15, 23, 42, .36);
                --revo-glass-shadow:
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
                border: 1px solid var(--revo-glass-border) !important;
                border-radius: 1.2rem !important;
                background: var(--revo-glass-bg) !important;
                box-shadow: var(--revo-glass-shadow);
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

            .revo-user-card {
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

            .revo-user-label {
                display: block;
                margin-bottom: .18rem;
                color: rgba(203, 213, 225, .68);
                font-size: .72rem;
                font-weight: 650;
                letter-spacing: .07em;
                text-transform: uppercase;
            }

            .revo-user-name {
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
    inject_app_styles()


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
    except (OperationalError, DatabaseSecurityError):
        apply_auth_layout()
        with st.container(key="auth_panel", horizontal_alignment="center"):
            st.title(
                "Banco de dados indisponível",
                text_alignment="center",
            )
            st.error(
                "O Revo não conseguiu validar a conexão segura com o PostgreSQL.",
                icon=":material/database_off:",
            )
            st.write(
                "A aplicação foi interrompida para não acessar dados com uma "
                "credencial administrativa ou sem isolamento RLS completo."
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
    """Apresenta login e cadastro em uma experiência dividida e responsiva."""
    apply_auth_layout()
    # Mudanças de widgets vinculados ao Session State precisam acontecer antes
    # de o widget ser instanciado nesta execução. O cadastro agenda a troca de
    # aba e o próximo rerun a aplica aqui, antes do segmented_control.
    pending_auth_mode = st.session_state.pop("auth_mode_pending", None)
    if pending_auth_mode in {"login", "signup"}:
        st.session_state.auth_mode = pending_auth_mode
        st.session_state.auth_mode_display = pending_auth_mode
    try:
        browser_theme_type = st.context.theme.type
    except (AttributeError, RuntimeError):
        browser_theme_type = "light" if st.session_state.theme_light else "dark"
    sync_browser_theme(
        key="revo_auth_theme_sync_instance",
        data={
            "light": bool(st.session_state.theme_light),
            "current": browser_theme_type,
            "paths": ["/"],
        },
    )
    current_mode = st.session_state.get(
        "auth_mode_display", st.session_state.get("auth_mode", "login")
    )
    is_signup = current_mode == "signup"
    with st.container(key="auth_card"):
        welcome_column, form_column = st.columns([1.08, 1], gap=None)
        with welcome_column:
            with st.container(key="auth_welcome"):
                st.html(
                    '<div class="auth-brand"><img src="app/static/revo-logo.png" '
                    'alt="Logo Revo"><span>Revo</span></div>'
                )
                with st.container(key="auth_story"):
                    st.html('<div class="auth-kicker">Sua vida financeira, mais clara</div>')
                    st.title(
                        "Comece sua jornada financeira"
                        if is_signup
                        else "Bem-vindo de volta"
                    )
                    st.write(
                        "Crie seu espaço seguro, registre sua rotina e acompanhe "
                        "sua evolução em um só lugar."
                        if is_signup
                        else "Retome sua visão financeira com organização, "
                        "privacidade e decisões mais conscientes."
                    )
                with st.container(key="auth_steps"):
                    st.caption("Seu caminho no Revo")
                    if is_signup:
                        st.markdown(":material/person_add: **1. Crie sua conta**")
                        st.markdown(":material/account_balance_wallet: 2. Organize sua rotina")
                        st.markdown(":material/monitoring: 3. Acompanhe sua evolução")
                    else:
                        st.markdown(":material/login: **1. Entre com segurança**")
                        st.markdown(":material/dashboard: 2. Consulte seu panorama")
                        st.markdown(":material/insights: 3. Decida com clareza")
        with form_column:
            with st.container(key="auth_form"):
                with st.container(
                    key="auth_toolbar",
                    horizontal=True,
                    horizontal_alignment="right",
                ):
                    st.toggle(
                        "Modo claro",
                        key="theme_light",
                        help="Alterna a tela de acesso entre os temas claro e escuro.",
                    )
                st.caption("ACESSO SEGURO · BETA 5.2")
                st.markdown(
                    "## Crie sua conta" if is_signup else "## Entre no Revo"
                )
                st.caption(
                    "Preencha seus dados para participar da beta fechada."
                    if is_signup
                    else "Acesse sua conta para continuar de onde parou."
                )
                flash = st.session_state.pop("flash", None)
                if flash:
                    (st.success if flash[0] == "success" else st.error)(flash[1])
                auth_mode = st.segmented_control(
                    "Tipo de acesso",
                    options=["login", "signup"],
                    default="login",
                    format_func=lambda option: (
                        ":material/login: Entrar"
                        if option == "login"
                        else ":material/person_add: Criar conta"
                    ),
                    key="auth_mode",
                    required=True,
                    label_visibility="collapsed",
                    width="stretch",
                    on_change=lambda: st.session_state.update(
                        auth_mode_display=st.session_state.auth_mode
                    ),
                )
                if auth_mode == "login":
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
                        key="auth_forgot",
                    ):
                        forgot_password()
                else:
                    with st.form("signup_form"):
                        name_column, email_column = st.columns(2, gap="small")
                        with name_column:
                            name = st.text_input(
                                "Seu nome",
                                placeholder="Como podemos chamar você?",
                            )
                        with email_column:
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
                        st.caption(
                            "Use 10 ou mais caracteres, com maiúscula, minúscula e número."
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
                                st.session_state.auth_mode_pending = "login"
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
try:
    browser_theme_type = st.context.theme.type
except (AttributeError, RuntimeError):
    browser_theme_type = "light" if st.session_state.theme_light else "dark"
sync_browser_theme(
    key="revo_browser_theme_sync_instance",
    data={
        "light": bool(st.session_state.theme_light),
        "current": browser_theme_type,
        "paths": [
            "/",
            "/home",
            "/dashboard",
            "/personal_finance",
            "/planning",
            "/investments",
            "/assistant",
            "/settings",
        ],
    },
)
mobile_navigation_gesture(key="mobile_navigation_gesture")
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
page = st.navigation(
    [home_page, dashboard_page, finance_page, planning_page, investments_page, help_page, settings_page],
    position="hidden",
)

with st.sidebar:
    st.html(
        '<div class="revo-brand"><img src="app/static/revo-logo.png" '
        'alt="Logo Revo"><span>Revo</span></div>'
    )
    st.page_link(home_page, label="Início", icon=":material/home:")
    st.page_link(dashboard_page, label=dashboard_title, icon=":material/dashboard:")
    st.html('<div class="fs-nav-section">Organizar</div>')
    st.page_link(finance_page, label="Finanças", icon=":material/account_balance_wallet:")
    st.page_link(planning_page, label="Planejamento", icon=":material/event_note:")
    st.page_link(investments_page, label="Investimentos", icon=":material/query_stats:")
    st.html('<div class="fs-nav-section">Conta</div>')
    st.page_link(help_page, label="Ajuda", icon=":material/help_center:")
    st.page_link(settings_page, label="Minha conta", icon=":material/manage_accounts:")

    with st.container(key="sidebar_account"):
        safe_user_name = escape(str(user["name"]))
        st.html(
            f"""
            <div class="revo-user-card">
                <span class="revo-user-label">Conectado como</span>
                <strong class="revo-user-name">{safe_user_name}</strong>
            </div>
            """
        )
        st.badge("Beta 5.2", icon=":material/science:", color="blue")
        st.toggle(
            "Modo claro",
            key="theme_light",
            help="Alterna toda a interface entre os temas claro e escuro.",
        )
        if st.button("Enviar feedback", icon=":material/rate_review:", width="stretch"):
            feedback_dialog()
        if st.button("Sair da conta", icon=":material/logout:", width="stretch"):
            st.session_state.clear()
            st.session_state.flash = ("success", "Sessão encerrada com segurança.")
            st.rerun()
        st.caption("Seus dados são separados por conta.")

page.run()
