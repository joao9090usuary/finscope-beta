"""Testes de configuração e apresentação específicas da Beta 5.1."""

import re
import unittest
from pathlib import Path

from utils.formatting import format_brl, format_decimal, format_percent
from utils.help_assistant import FALLBACK_RESPONSE, answer_help_question


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BetaConfigurationTest(unittest.TestCase):
    """Confirma que o chat funciona localmente e sem inteligência artificial."""

    def test_help_page_has_chat_without_ai_calls(self) -> None:
        """A página deve aceitar perguntas sem importar provedores de IA."""
        source = (PROJECT_ROOT / "app_pages" / "assistant.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("st.chat_input", source)
        self.assertIn("answer_help_question", source)
        self.assertNotIn("answer_with_ai", source)
        self.assertNotIn("OpenAI", source)

    def test_local_help_answers_known_and_unknown_questions(self) -> None:
        """O mecanismo deve orientar temas conhecidos e oferecer uma lista no fallback."""
        answer = answer_help_question("Como registro um gasto?")

        self.assertIn("Finanças pessoais", answer)
        self.assertNotIn("criar sua conta", answer)
        self.assertEqual(answer_help_question("xyz"), FALLBACK_RESPONSE)

    def test_brazilian_number_formatting(self) -> None:
        """Valores devem utilizar milhar com ponto e decimal com vírgula."""
        self.assertEqual(format_decimal(1234.5), "1.234,50")
        self.assertEqual(format_brl(1234.5), "R$ 1.234,50")
        self.assertEqual(format_percent(12.34), "12,3%")

    def test_docker_synchronizes_an_existing_database_password(self) -> None:
        """O aplicativo deve aguardar a senha do volume ser sincronizada."""
        compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")

        self.assertIn("database_password_sync:", compose)
        self.assertIn("database_migrate:", compose)
        self.assertIn('["python", "-m", "jobs.init_database"]', compose)
        self.assertIn("service_completed_successfully", compose)
        self.assertIn("ALTER ROLE finscope", compose)
        self.assertIn("NOBYPASSRLS", compose)
        self.assertIn("postgresql+psycopg://finscope_app:", compose)
        self.assertIn("except (OperationalError, DatabaseSecurityError):", entrypoint)
        self.assertNotIn("st.exception", entrypoint)

    def test_postgres_row_security_is_forced(self) -> None:
        """As tabelas particulares devem usar política de negação por padrão."""
        database_source = (PROJECT_ROOT / "utils" / "database.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("ENABLE ROW LEVEL SECURITY", database_source)
        self.assertIn("FORCE ROW LEVEL SECURITY", database_source)
        self.assertIn("current_setting('finscope.user_id'", database_source)
        self.assertIn('set_config("revo.user_id"', database_source)

    def test_sast_findings_do_not_return(self) -> None:
        """Impede a reintrodução dos padrões sinalizados pela varredura externa."""
        database_source = (PROJECT_ROOT / "utils" / "database.py").read_text(
            encoding="utf-8"
        )
        pdf_source = (PROJECT_ROOT / "utils" / "pdf_report.py").read_text(
            encoding="utf-8"
        )
        python_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in PROJECT_ROOT.rglob("*.py")
            if ".venv" not in path.parts and "__pycache__" not in path.parts
        )

        self.assertIsNone(re.search(r"\btext\s*\(", database_source))
        self.assertNotIn("xml.sax", pdf_source)
        self.assertIsNone(re.search(r"\bexec\s*\(", python_sources))
        self.assertFalse((PROJECT_ROOT / "app.py").exists())
        self.assertIn("pg_sql.Identifier(runtime_role)", database_source)

    def test_browser_security_does_not_enable_arbitrary_javascript(self) -> None:
        """O ponto de entrada não deve liberar execução de JavaScript injetado."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(
            encoding="utf-8"
        )
        investments = (PROJECT_ROOT / "app_pages" / "investments.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("unsafe_allow_javascript=True", entrypoint)
        self.assertIn("enableXsrfProtection = true", config)
        self.assertIn("enableCORS = true", config)
        self.assertIn("Esqueceu sua senha?", entrypoint)
        self.assertNotIn("with st.skeleton", investments)

    def test_home_glass_styles_escape_the_user_name(self) -> None:
        """O acabamento compartilhado deve preservar acessibilidade e dados pessoais."""
        home = (PROJECT_ROOT / "app_pages" / "home.py").read_text(encoding="utf-8")
        shared_ui = (PROJECT_ROOT / "utils" / "ui.py").read_text(encoding="utf-8")
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")

        self.assertIn("backdrop-filter:blur", shared_ui)
        self.assertIn("fs-page-header__highlight", shared_ui)
        self.assertIn("metric_card_grid", home)
        self.assertIn('st.columns([1.55, 1], gap="medium")', home)
        self.assertIn("safe_title = escape(title)", shared_ui)
        self.assertIn("first_name = escape(user_name.split()[0])", shared_ui)
        self.assertIn('escape(str(user["name"]))', entrypoint)
        self.assertIn('div[role="dialog"]', shared_ui)
        self.assertIn("prefers-reduced-motion", shared_ui)
        dashboard = (PROJECT_ROOT / "app_pages" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("page_header(", dashboard)

    def test_authenticated_pages_share_the_compact_design_system(self) -> None:
        """Os componentes comuns devem usar superfícies discretas e a mesma escala."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        dashboard = (PROJECT_ROOT / "app_pages" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        shared_ui = (PROJECT_ROOT / "utils" / "ui.py").read_text(encoding="utf-8")
        config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(
            encoding="utf-8"
        )
        finance = (PROJECT_ROOT / "app_pages" / "personal_finance.py").read_text(
            encoding="utf-8"
        )
        investments = (PROJECT_ROOT / "app_pages" / "investments.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("inject_app_styles()", entrypoint)
        self.assertIn("--fs-canvas", shared_ui)
        self.assertIn("max-width: none", shared_ui)
        self.assertIn('[data-testid="stVerticalBlockBorderWrapper"]', shared_ui)
        self.assertIn('[data-testid="stMetric"]', shared_ui)
        self.assertIn('baseRadius = "8px"', config)
        self.assertIn('buttonRadius = "6px"', config)
        self.assertIn("metric_card_grid(", finance)
        self.assertIn("metric_card_grid(", investments)

    def test_sidebar_and_mobile_navigation_remain_available(self) -> None:
        """A navegação deve recolher, fechar ao trocar de página e sumir no login."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        shared_ui = (PROJECT_ROOT / "utils" / "ui.py").read_text(encoding="utf-8")

        self.assertIn('position="hidden"', entrypoint)
        self.assertIn("st.page_link(home_page", entrypoint)
        self.assertIn('initial_sidebar_state="expanded"', entrypoint)
        self.assertIn("onSidebarNavigation", entrypoint)
        self.assertIn('document.addEventListener("touchstart"', entrypoint)
        self.assertIn('[data-testid="stSidebarCollapsedControl"]', shared_ui)
        self.assertIn(".fs-kpi-grid", shared_ui)
        self.assertIn("grid-template-columns:repeat(2", shared_ui)

    def test_financial_charts_keep_semantic_colors_and_dynamic_shapes(self) -> None:
        """Receitas, despesas, saldo e indicadores devem manter cores reconhecíveis."""
        dashboard = (PROJECT_ROOT / "app_pages" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        finance = (PROJECT_ROOT / "app_pages" / "personal_finance.py").read_text(
            encoding="utf-8"
        )
        investments = (PROJECT_ROOT / "app_pages" / "investments.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("mark_area", dashboard)
        self.assertIn("mark_arc", dashboard)
        self.assertIn('["#34D399", "#FB7185", "#60A5FA"]', dashboard)
        self.assertIn("mark_area", finance)
        self.assertIn("import pandas as pd", finance)
        self.assertIn('FLOW_COLORS = ["#34D399", "#FB7185"]', finance)
        self.assertIn("innerRadius=72", finance)
        self.assertIn("price_area", investments)
        self.assertIn('["#60A5FA", "#FBBF24", "#8176FF"]', investments)

    def test_light_theme_reaches_native_widgets_and_every_chart(self) -> None:
        """O modo claro não pode deixar gráficos ou superfícies nativas escuras."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        shared_ui = (PROJECT_ROOT / "utils" / "ui.py").read_text(encoding="utf-8")
        config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(
            encoding="utf-8"
        )
        chart_pages = [
            PROJECT_ROOT / "app_pages" / "home.py",
            PROJECT_ROOT / "app_pages" / "dashboard.py",
            PROJECT_ROOT / "app_pages" / "personal_finance.py",
            PROJECT_ROOT / "app_pages" / "investments.py",
        ]

        self.assertIn("revo_browser_theme_sync", entrypoint)
        self.assertIn('const desired = data?.light ? "Light" : "Dark"', entrypoint)
        self.assertIn('role="menuitemradio"', entrypoint)
        self.assertNotIn("window.location.reload()", entrypoint)
        self.assertIn('[theme.light]', config)
        self.assertIn('backgroundColor = "#F3F6FB"', config)
        self.assertIn('secondaryBackgroundColor = "#FFFFFF"', config)
        self.assertIn("fs-card-enter", shared_ui)
        self.assertIn("fs-chart-enter", shared_ui)
        self.assertIn("prefers-reduced-motion", shared_ui)
        self.assertIn("background:var(--fs-surface)!important", shared_ui)
        for page in chart_pages:
            source = page.read_text(encoding="utf-8")
            self.assertIn('.configure(background=theme["surface"])', source)
            self.assertIn("theme=None", source)

    def test_authentication_layout_is_theme_aware_and_responsive(self) -> None:
        """Login e cadastro devem compartilhar contraste e adaptação móvel."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        auth_visual = PROJECT_ROOT / "static" / "revo-auth-visual.png"

        self.assertTrue(auth_visual.exists())
        self.assertGreater(auth_visual.stat().st_size, 100_000)
        self.assertIn("--auth-canvas", entrypoint)
        self.assertIn("--auth-surface", entrypoint)
        self.assertIn('url("app/static/revo-auth-visual.png")', entrypoint)
        self.assertIn('st.segmented_control(', entrypoint)
        self.assertIn('key="auth_mode"', entrypoint)
        self.assertIn('key="theme_light"', entrypoint)
        self.assertIn('key="auth_forgot"', entrypoint)
        self.assertIn("revo_auth_theme_sync_instance", entrypoint)
        self.assertIn("prefers-reduced-motion: reduce", entrypoint)
        self.assertIn("max-width: 820px", entrypoint)
        self.assertIn("max-height: 720px", entrypoint)
        self.assertIn("font-size: 16px !important", entrypoint)
        self.assertIn(
            'pending_auth_mode = st.session_state.pop("auth_mode_pending", None)',
            entrypoint,
        )
        self.assertIn(
            'st.session_state.auth_mode = pending_auth_mode', entrypoint
        )
        self.assertIn(
            'st.session_state.auth_mode_pending = "login"', entrypoint
        )
        self.assertNotIn('st.session_state.auth_mode = "login"', entrypoint)
        self.assertIn('menuButton.getAttribute("aria-expanded") === "true"', entrypoint)

    def test_end_user_audit_regressions_are_covered(self) -> None:
        """Fluxos vazios, ajuda, navegação e movimento devem permanecer estáveis."""
        finance = (PROJECT_ROOT / "app_pages" / "personal_finance.py").read_text(
            encoding="utf-8"
        )
        help_page = (PROJECT_ROOT / "app_pages" / "assistant.py").read_text(
            encoding="utf-8"
        )
        planning = (PROJECT_ROOT / "app_pages" / "planning.py").read_text(
            encoding="utf-8"
        )
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        dashboard = (PROJECT_ROOT / "app_pages" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        shared_ui = (PROJECT_ROOT / "utils" / "ui.py").read_text(encoding="utf-8")

        self.assertIn('columns=["id", "Data", "Tipo", "Categoria", "Descrição", "Valor"]', finance)
        self.assertIn("on_change=_queue_selected_suggestion", help_page)
        self.assertNotIn("if selected:\n            st.session_state.help_pending_prompt", help_page)
        self.assertIn("_quantity_label", planning)
        self.assertIn("_progress_money", planning)
        self.assertIn("window.scrollTo({ top: 0", entrypoint)
        self.assertIn("auth_mode_display", entrypoint)
        self.assertIn("ativo acompanhado", dashboard)
        self.assertIn("fs-section-enter", shared_ui)
        self.assertIn("fs-dialog-enter", shared_ui)
        self.assertIn("prefers-reduced-motion", shared_ui)

    def test_revo_brand_replaces_the_legacy_identity(self) -> None:
        """A marca anterior não deve reaparecer em código, conteúdo ou ativos."""
        legacy_brand = "Fin" + "Scope"
        # Identificadores internos do banco continuam com o nome legado para que
        # volumes, papeis e politicas RLS publicados nao percam compatibilidade.
        # A verificacao cobre apenas superficies apresentadas ao usuario.
        text_files = [
            PROJECT_ROOT / "streamlit_app.py",
            PROJECT_ROOT / "static" / "manifest.webmanifest",
            PROJECT_ROOT / "utils" / "email_service.py",
            PROJECT_ROOT / "utils" / "pdf_report.py",
            *sorted((PROJECT_ROOT / "app_pages").glob("*.py")),
        ]
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore") for path in text_files
        )

        self.assertNotIn(legacy_brand, combined)
        self.assertNotIn(legacy_brand.lower(), combined.lower())
        self.assertIn('page_title="Revo"', combined)
        self.assertTrue((PROJECT_ROOT / "static" / "revo-logo.png").is_file())
        self.assertTrue(
            (PROJECT_ROOT / "static" / "revo-auth-visual.png").is_file()
        )
        self.assertFalse(
            (PROJECT_ROOT / "static" / (legacy_brand.lower() + "-icon.svg")).exists()
        )


if __name__ == "__main__":
    unittest.main()
