"""Regressões para as correções indicadas pela análise estática externa."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy.dialects import postgresql

from utils.database import (
    DatabaseSecurityError,
    _TENANT_TABLES,
    _assert_runtime_postgres_security,
    _configure_postgres_security,
)


class _RecordingCursor:
    """Cursor mínimo que registra SQL composto sem abrir uma conexão real."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def execute(self, statement) -> None:
        self.statements.append(statement.as_string())


class _RecordingConnection:
    """Conexão mínima para compilar DDL com o dialeto PostgreSQL."""

    def __init__(self) -> None:
        self.ddl: list[str] = []
        self.cursor = _RecordingCursor()
        self.connection = type(
            "ConnectionProxy",
            (),
            {
                "driver_connection": type(
                    "DriverConnection",
                    (),
                    {"cursor": lambda _self: self.cursor},
                )()
            },
        )()

    def execute(self, statement) -> None:
        self.ddl.append(str(statement.compile(dialect=postgresql.dialect())))


class _MappingResult:
    """Resultado mínimo compatível com ``mappings()`` do SQLAlchemy."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self):
        return self

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class _RuntimeSecurityConnection:
    """Fornece o papel e o estado RLS sem depender de PostgreSQL real."""

    def __init__(
        self,
        *,
        superuser: bool = False,
        bypass_rls: bool = False,
        protected_tables: tuple[str, ...] = _TENANT_TABLES,
    ) -> None:
        self.results = [
            _MappingResult(
                [
                    {
                        "rolname": "finscope_app",
                        "rolsuper": superuser,
                        "rolbypassrls": bypass_rls,
                        "rolcreatedb": False,
                        "rolcreaterole": False,
                    }
                ]
            ),
            _MappingResult([]),
            _MappingResult(
                [
                    {
                        "relname": name,
                        "relrowsecurity": True,
                        "relforcerowsecurity": True,
                    }
                    for name in protected_tables
                ]
            ),
        ]

    def execute(self, statement):
        str(statement.compile(dialect=postgresql.dialect()))
        return self.results.pop(0)


class SecurityRegressionTest(unittest.TestCase):
    """Confirma que a proteção PostgreSQL permanece segura e compilável."""

    def test_rls_ddl_compiles_for_every_private_table(self) -> None:
        """Cada tabela particular deve receber quatro comandos de proteção."""
        connection = _RecordingConnection()

        with patch.dict(os.environ, {"APP_DATABASE_ROLE": ""}):
            _configure_postgres_security(connection)

        self.assertEqual(len(connection.ddl), len(_TENANT_TABLES) * 4)
        compiled = "\n".join(connection.ddl)
        self.assertIn("ENABLE ROW LEVEL SECURITY", compiled)
        self.assertIn("FORCE ROW LEVEL SECURITY", compiled)
        self.assertIn("CREATE POLICY tenant_isolation", compiled)

    def test_runtime_role_is_composed_as_an_identifier(self) -> None:
        """O nome do papel deve ser citado pelo psycopg, nunca concatenado."""
        connection = _RecordingConnection()

        with patch.dict(os.environ, {"APP_DATABASE_ROLE": "finscope_app"}):
            _configure_postgres_security(connection)

        self.assertEqual(len(connection.cursor.statements), 2)
        self.assertTrue(
            all('TO "finscope_app"' in statement for statement in connection.cursor.statements)
        )

    def test_invalid_runtime_role_is_rejected(self) -> None:
        """Um valor malicioso no ambiente não pode alcançar um comando GRANT."""
        connection = _RecordingConnection()

        with patch.dict(
            os.environ,
            {"APP_DATABASE_ROLE": 'finscope_app"; DROP TABLE users; --'},
        ):
            with self.assertRaises(RuntimeError):
                _configure_postgres_security(connection)

        self.assertEqual(connection.ddl, [])
        self.assertEqual(connection.cursor.statements, [])

    def test_restricted_runtime_role_with_complete_rls_is_accepted(self) -> None:
        """O aplicativo pode iniciar somente com papel restrito e RLS completo."""
        _assert_runtime_postgres_security(_RuntimeSecurityConnection())

    def test_runtime_role_with_bypass_rls_is_rejected(self) -> None:
        """Uma credencial proprietária ou BYPASSRLS deve bloquear o aplicativo."""
        with self.assertRaises(DatabaseSecurityError):
            _assert_runtime_postgres_security(
                _RuntimeSecurityConnection(bypass_rls=True)
            )

    def test_missing_rls_table_is_rejected(self) -> None:
        """Nenhuma tabela particular pode ficar fora do isolamento obrigatório."""
        with self.assertRaises(DatabaseSecurityError):
            _assert_runtime_postgres_security(
                _RuntimeSecurityConnection(protected_tables=_TENANT_TABLES[:-1])
            )


if __name__ == "__main__":
    unittest.main()
