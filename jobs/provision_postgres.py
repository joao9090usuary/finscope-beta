"""Provisiona um papel PostgreSQL restrito e aplica as políticas RLS.

Este comando é administrativo e deve ser executado separadamente do processo
web. Nenhuma credencial é impressa ou gravada em arquivo.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import psycopg
from psycopg import sql


_ROLE_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def _required_secret(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"Defina {name} antes de executar o provisionamento.")
    if _CONTROL_CHARACTERS.search(value):
        raise RuntimeError(f"{name} contém caracteres de controle inválidos.")
    return value


def _validate_migration_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeError("MIGRATION_DATABASE_URL deve ser uma URL PostgreSQL válida.")
    return value


def provision_runtime_role(
    migration_url: str,
    role_name: str,
    role_password: str,
) -> None:
    """Cria ou atualiza um papel LOGIN sem privilégios capazes de ignorar RLS."""
    if not _ROLE_NAME.fullmatch(role_name):
        raise RuntimeError("APP_DATABASE_ROLE possui formato inválido.")
    if len(role_password) < 32:
        raise RuntimeError("POSTGRES_APP_PASSWORD deve ter pelo menos 32 caracteres.")

    role = sql.Identifier(role_name)
    password = sql.Literal(role_password)
    with psycopg.connect(_validate_migration_url(migration_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)",
                (role_name,),
            )
            exists = bool(cursor.fetchone()[0])
            if exists:
                role_statement = sql.SQL(
                    "ALTER ROLE {} WITH LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
                )
            else:
                role_statement = sql.SQL(
                    "CREATE ROLE {} WITH LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
                )
            cursor.execute(role_statement.format(role, password))
            cursor.execute("SELECT current_database()")
            database_name = str(cursor.fetchone()[0])
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name),
                    role,
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role)
            )
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")


def main() -> None:
    """Provisiona o papel e executa migrações com a credencial proprietária."""
    migration_url = _required_secret("MIGRATION_DATABASE_URL")
    role_password = _required_secret("POSTGRES_APP_PASSWORD")
    # O nome legado e um identificador interno do banco, nao a marca do produto.
    role_name = os.getenv("APP_DATABASE_ROLE", "finscope_app").strip()
    provision_runtime_role(migration_url, role_name, role_password)

    # O módulo cria o engine no import; configure o ambiente antes de importá-lo.
    os.environ["DATABASE_URL"] = migration_url
    os.environ["DATABASE_MIGRATIONS_ENABLED"] = "true"
    os.environ["APP_DATABASE_ROLE"] = role_name
    from utils.database import init_db

    init_db()
    print("Papel restrito criado e políticas RLS aplicadas com sucesso.")


if __name__ == "__main__":
    main()
