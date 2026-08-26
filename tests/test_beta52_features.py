"""Testes dos recursos de planejamento e portabilidade da Beta 5.2."""

import os
import unittest
from datetime import date
from io import BytesIO
from zipfile import ZipFile

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BETA_MAX_USERS", "10")
os.environ.setdefault("BETA_INVITE_CODE", "convite-seguro-de-teste")
os.environ.setdefault("APP_ENV", "development")

from utils.data_portability import build_account_export, import_transactions_csv  # noqa: E402
from utils.database import (  # noqa: E402
    authenticate,
    budgets_frame,
    confirm_recurring_entry,
    create_goal,
    create_recurring_entry,
    create_user,
    delete_recurring_entry,
    delete_user_account,
    feedback_frame,
    get_user_preference,
    goals_frame,
    init_db,
    recurring_frame,
    save_budget,
    set_weekly_summary,
    submit_feedback,
    transactions_frame,
)


class Beta52FeaturesTest(unittest.TestCase):
    """Valida isolamento, duplicidade e portabilidade dos novos recursos."""

    @classmethod
    def setUpClass(cls) -> None:
        init_db()
        ok, _ = create_user(
            "Pessoa Planejamento",
            "planejamento@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        assert ok
        cls.user = authenticate("planejamento@example.com", "SenhaInicial123")
        ok, _ = create_user(
            "Outra Conta",
            "outra-conta@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        assert ok
        cls.other_user = authenticate("outra-conta@example.com", "SenhaInicial123")

    def test_planning_and_feedback_are_persisted(self) -> None:
        save_budget(self.user["id"], "Alimentação", 900)
        create_goal(self.user["id"], "Reserva", 5_000, 500)
        submit_feedback(self.user["id"], "Sugestão", "Gostaria de mais filtros.", 9, "Dashboard")

        self.assertEqual(budgets_frame(self.user["id"]).iloc[0]["Limite"], 900)
        self.assertEqual(goals_frame(self.user["id"]).iloc[0]["Meta"], "Reserva")
        self.assertEqual(feedback_frame(self.user["id"]).iloc[0]["Nota"], 9)

    def test_recurring_confirmation_is_idempotent(self) -> None:
        previous_count = len(transactions_frame(self.user["id"]))
        create_recurring_entry(
            self.user["id"], "Receita", 2_000, "Salário", "Salário mensal", date.today().day
        )
        recurring_id = int(recurring_frame(self.user["id"]).iloc[0]["id"])

        first = confirm_recurring_entry(self.user["id"], recurring_id, date.today())
        second = confirm_recurring_entry(self.user["id"], recurring_id, date.today())

        self.assertTrue(first[0])
        self.assertFalse(second[0])
        self.assertEqual(len(transactions_frame(self.user["id"])), previous_count + 1)

    def test_recurring_id_cannot_delete_another_users_data(self) -> None:
        """Um ID de outra conta não deve remover recorrência nem ocorrências relacionadas."""
        create_recurring_entry(
            self.other_user["id"],
            "Despesa",
            300,
            "Contas",
            "Conta protegida",
            date.today().day,
        )
        other_id = int(recurring_frame(self.other_user["id"]).iloc[0]["id"])
        confirm_recurring_entry(self.other_user["id"], other_id, date.today())

        with self.assertRaises(ValueError):
            delete_recurring_entry(self.user["id"], other_id)

        remaining = recurring_frame(self.other_user["id"])
        self.assertIn(other_id, remaining["id"].astype(int).tolist())

    def test_preferences_export_and_import(self) -> None:
        set_weekly_summary(self.user["id"], True)
        self.assertTrue(get_user_preference(self.user["id"])["weekly_summary_enabled"])

        archive = build_account_export(self.user)
        with ZipFile(BytesIO(archive)) as zip_file:
            self.assertIn("lancamentos.csv", zip_file.namelist())
            self.assertNotIn(b"password", archive.lower())

        csv_data = (
            "Tipo,Valor,Categoria,Descrição,Data\n"
            f"Despesa,25.50,Transporte,Ônibus,{date.today():%d/%m/%Y}\n"
        )
        imported, errors = import_transactions_csv(self.user["id"], csv_data.encode("utf-8"))
        self.assertEqual(imported, 1)
        self.assertEqual(errors, [])

    def test_z_account_deletion_removes_access(self) -> None:
        """A exclusão permanente deve impedir um novo login."""
        delete_user_account(self.user["id"])
        self.assertIsNone(authenticate("planejamento@example.com", "SenhaInicial123"))


if __name__ == "__main__":
    unittest.main()
