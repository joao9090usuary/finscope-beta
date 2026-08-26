"""Testes da dashboard individual e do relatório financeiro em PDF."""

import os
import unittest
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
from pypdf import PdfReader

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BETA_MAX_USERS", "10")
os.environ.setdefault("BETA_INVITE_CODE", "convite-seguro-de-teste")
os.environ.setdefault("APP_ENV", "development")

from utils.database import (  # noqa: E402
    add_transaction,
    create_dashboard,
    create_user,
    delete_dashboard,
    get_dashboard,
    holdings_frame,
    init_db,
    transactions_frame,
    update_dashboard_period,
)
from utils.pdf_report import build_financial_report  # noqa: E402


class DashboardTest(unittest.TestCase):
    """Valida isolamento, período, exclusão e exportação da dashboard."""

    @classmethod
    def setUpClass(cls) -> None:
        """Cria duas contas independentes para os cenários da dashboard."""
        init_db()
        create_user(
            "Pessoa Dashboard A",
            "dashboard-a@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        create_user(
            "Pessoa Dashboard B",
            "dashboard-b@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        from utils.database import authenticate

        cls.user_a = authenticate("dashboard-a@example.com", "SenhaInicial123")
        cls.user_b = authenticate("dashboard-b@example.com", "SenhaInicial123")

    def tearDown(self) -> None:
        """Evita que a configuração de um teste interfira no seguinte."""
        delete_dashboard(self.user_a["id"])
        delete_dashboard(self.user_b["id"])

    def test_dashboard_is_private_and_keeps_financial_data_when_deleted(self) -> None:
        """A configuração deve ser individual e não possuir exclusão em cascata reversa."""
        ok, _ = create_dashboard(self.user_a["id"], 3)
        self.assertTrue(ok)
        self.assertEqual(get_dashboard(self.user_a["id"])["preferred_period"], 3)
        self.assertIsNone(get_dashboard(self.user_b["id"]))

        add_transaction(
            self.user_a["id"],
            "Receita",
            3_500,
            "Salário",
            "Salário mensal",
            date.today(),
        )
        update_dashboard_period(self.user_a["id"], 6)
        self.assertEqual(get_dashboard(self.user_a["id"])["preferred_period"], 6)

        delete_dashboard(self.user_a["id"])
        self.assertIsNone(get_dashboard(self.user_a["id"]))
        self.assertEqual(len(transactions_frame(self.user_a["id"])), 1)

    def test_transaction_period_filter_excludes_older_records(self) -> None:
        """O banco deve retornar somente registros a partir da data solicitada."""
        add_transaction(
            self.user_b["id"],
            "Despesa",
            120,
            "Alimentação",
            "Compra recente",
            date.today(),
        )
        add_transaction(
            self.user_b["id"],
            "Despesa",
            80,
            "Transporte",
            "Compra antiga",
            date.today() - timedelta(days=70),
        )

        filtered = transactions_frame(
            self.user_b["id"],
            start_date=date.today() - timedelta(days=30),
        )

        self.assertEqual(filtered["Descrição"].tolist(), ["Compra recente"])

    def test_pdf_contains_user_and_financial_sections(self) -> None:
        """O arquivo exportado deve ser um PDF legível com as áreas essenciais."""
        transactions = pd.DataFrame(
            [
                {
                    "id": 1,
                    "Tipo": "Receita",
                    "Valor": 4_200.0,
                    "Categoria": "Salário",
                    "Descrição": "Salário mensal",
                    "Data": date.today(),
                },
                {
                    "id": 2,
                    "Tipo": "Despesa",
                    "Valor": 980.0,
                    "Categoria": "Moradia",
                    "Descrição": "Aluguel",
                    "Data": date.today(),
                },
            ]
        )
        pdf_bytes = build_financial_report(
            user=self.user_a,
            months=1,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
            transactions=transactions,
            holdings=holdings_frame(self.user_a["id"]),
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("FinScope", text)
        self.assertIn("Pessoa Dashboard A", text)
        self.assertIn("Movimentações do período", text)

    def test_invalid_dashboard_period_is_rejected(self) -> None:
        """A preferência deve aceitar somente os intervalos oferecidos na interface."""
        ok, message = create_dashboard(self.user_a["id"], 2)
        self.assertFalse(ok)
        self.assertIn("inválido", message)


if __name__ == "__main__":
    unittest.main()
