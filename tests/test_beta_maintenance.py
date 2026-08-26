"""Testes de configuração e apresentação específicas da Beta 5.1."""

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
        self.assertIn("except OperationalError:", entrypoint)
        self.assertNotIn("st.exception", entrypoint)

    def test_postgres_row_security_is_forced(self) -> None:
        """As tabelas particulares devem usar política de negação por padrão."""
        database_source = (PROJECT_ROOT / "utils" / "database.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("ENABLE ROW LEVEL SECURITY", database_source)
        self.assertIn("FORCE ROW LEVEL SECURITY", database_source)
        self.assertIn("current_setting('finscope.user_id'", database_source)

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
        """O novo acabamento deve preservar acessibilidade e escapar dados pessoais."""
        home = (PROJECT_ROOT / "app_pages" / "home.py").read_text(encoding="utf-8")
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")

        self.assertIn("backdrop-filter: blur", home)
        self.assertIn("home-user-gradient", home)
        self.assertIn("height: 10rem", home)
        self.assertIn("padding: clamp(1.15rem", home)
        self.assertIn("padding-top: clamp(3.25rem, 6.5vh, 5rem)", home)
        self.assertIn('st.columns(2, gap="medium")', home)
        self.assertIn('escape(str(user["name"])', home)
        self.assertIn('escape(str(user["name"]))', entrypoint)
        self.assertIn('div[role="dialog"]', entrypoint)
        self.assertIn("prefers-reduced-motion", home)
        dashboard = (PROJECT_ROOT / "app_pages" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("padding-top: clamp(3.25rem, 6.5vh, 5rem)", dashboard)

    def test_authenticated_pages_share_the_glass_design_system(self) -> None:
        """Os componentes comuns devem seguir as mesmas dimensões e superfícies."""
        entrypoint = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(
            encoding="utf-8"
        )
        finance = (PROJECT_ROOT / "app_pages" / "personal_finance.py").read_text(
            encoding="utf-8"
        )
        investments = (PROJECT_ROOT / "app_pages" / "investments.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("--finscope-glass-bg", entrypoint)
        self.assertIn('[data-testid="stVerticalBlockBorderWrapper"]', entrypoint)
        self.assertIn('[role="tabpanel"]', entrypoint)
        self.assertIn('[data-testid="stMetric"]', entrypoint)
        self.assertIn('baseRadius = "14px"', config)
        self.assertIn('buttonRadius = "12px"', config)
        self.assertIn('st.columns(4, gap="medium")', finance)
        self.assertIn('st.columns(4, gap="medium")', investments)

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
        self.assertIn('FLOW_COLORS = ["#22C55E", "#FB7185"]', finance)
        self.assertIn("innerRadius=72", finance)
        self.assertIn("price_area", investments)
        self.assertIn('["#60A5FA", "#FBBF24", "#A78BFA"]', investments)


if __name__ == "__main__":
    unittest.main()
