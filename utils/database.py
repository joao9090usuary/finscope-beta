"""Camada de persistência do FinScope (SQLite local ou PostgreSQL)."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import unicodedata
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import bcrypt
import pandas as pd
from psycopg import sql as pg_sql
from sqlalchemy import (
    DDL,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    column,
    create_engine,
    delete,
    func,
    inspect,
    select,
    table,
    update,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.exc import IntegrityError


TRANSACTION_CATEGORIES = {
    "Receita": ("Salário", "Freelance", "Rendimentos", "Outros ganhos"),
    "Despesa": (
        "Moradia",
        "Alimentação",
        "Transporte",
        "Saúde",
        "Educação",
        "Lazer",
        "Compras",
        "Contas",
        "Outros gastos",
    ),
}


def utcnow() -> datetime:
    """UTC sem fuso para compatibilidade uniforme entre SQLite e PostgreSQL."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Classe-base dos modelos persistidos pelo SQLAlchemy."""

    pass


class User(Base):
    """Conta de uma pessoa participante da beta."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Campo legado reservado para a futura reativação da verificação de e-mail.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuthToken(Base):
    """Token de uso único para recuperação e futuros fluxos de autenticação."""

    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LoginThrottle(Base):
    """Bloqueio persistente contra tentativas repetidas de login."""

    __tablename__ = "login_throttles"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Transaction(Base):
    """Receita ou despesa pertencente a uma conta."""

    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(160), default="")
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Holding(Base):
    """Posição de um portfólio virtual pertencente a uma conta."""

    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_holding_user_ticker"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Dashboard(Base):
    """Preferências da dashboard particular de uma conta."""

    __tablename__ = "dashboards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    preferred_period: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    """Relato enviado por uma pessoa participante da beta."""

    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page: Mapped[str] = mapped_column(String(60), default="")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Budget(Base):
    """Limite mensal de gasto por categoria."""

    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_budget_user_category"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    monthly_limit: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SavingsGoal(Base):
    """Meta financeira particular de uma conta."""

    __tablename__ = "savings_goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    target_amount: Mapped[float] = mapped_column(Float)
    saved_amount: Mapped[float] = mapped_column(Float, default=0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecurringEntry(Base):
    """Previsão mensal que pode ser confirmada como lançamento real."""

    __tablename__ = "recurring_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(160), default="")
    day_of_month: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecurringOccurrence(Base):
    """Confirmação idempotente de uma recorrência em determinada data."""

    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint("recurring_entry_id", "occurred_on", name="uq_recurring_occurrence"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    recurring_entry_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_entries.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), unique=True
    )
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserPreference(Base):
    """Preferências de comunicação e privacidade da conta."""

    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    weekly_summary_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SecurityEvent(Base):
    """Evento mínimo de auditoria, sem senhas, tokens ou dados financeiros."""

    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    identity_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    detail: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


DASHBOARD_PERIODS = {1, 3, 6, 12}
FEEDBACK_CATEGORIES = {"Erro", "Sugestão", "Elogio", "Outro"}

_TENANT_TABLES = (
    "transactions",
    "holdings",
    "dashboards",
    "feedback",
    "budgets",
    "savings_goals",
    "recurring_entries",
    "recurring_occurrences",
    "user_preferences",
)
_PLAIN_TEXT_MARKUP = re.compile(r"<[^>]{0,512}>")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ROLE_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

_PG_ROLES = table(
    "pg_roles",
    column("rolname", String),
    column("oid", Integer),
    column("rolsuper", Boolean),
    column("rolbypassrls", Boolean),
    column("rolcreatedb", Boolean),
    column("rolcreaterole", Boolean),
    schema="pg_catalog",
)
_PG_CLASS = table(
    "pg_class",
    column("relname", String),
    column("relrowsecurity", Boolean),
    column("relforcerowsecurity", Boolean),
    column("relnamespace", Integer),
    schema="pg_catalog",
)
_PG_NAMESPACE = table(
    "pg_namespace",
    column("oid", Integer),
    column("nspname", String),
    schema="pg_catalog",
)


class DatabaseSecurityError(RuntimeError):
    """Impede a inicialização com um papel capaz de contornar o isolamento."""


def _clean_plain_text(
    value: str,
    *,
    field: str,
    maximum: int,
    minimum: int = 0,
    collapse_whitespace: bool = True,
) -> str:
    """Normaliza texto simples e rejeita controles ou marcação ativa."""
    normalized = unicodedata.normalize("NFKC", str(value))
    if _CONTROL_CHARACTERS.search(normalized) or _PLAIN_TEXT_MARKUP.search(normalized):
        raise ValueError(f"{field} contém caracteres não permitidos.")
    cleaned = (
        " ".join(normalized.strip().split())
        if collapse_whitespace
        else normalized.strip()
    )
    if not minimum <= len(cleaned) <= maximum:
        raise ValueError(f"{field} deve ter entre {minimum} e {maximum} caracteres.")
    return cleaned


def _normalize_email(email: str) -> str:
    """Normaliza e valida um endereço usado em autenticação e cabeçalhos."""
    normalized = unicodedata.normalize("NFKC", str(email)).strip().lower()
    if (
        _CONTROL_CHARACTERS.search(normalized)
        or len(normalized) > 180
        or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized)
    ):
        raise ValueError("Informe um e-mail válido.")
    return normalized


def _set_rls_context(session: Session, user_id: int) -> None:
    """Vincula a transação PostgreSQL à conta autorizada pelo servidor."""
    safe_user_id = int(user_id)
    if safe_user_id <= 0:
        raise PermissionError("Contexto de conta inválido.")
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            select(func.set_config("finscope.user_id", str(safe_user_id), True))
        )


def _configure_postgres_security(connection) -> None:
    """Ativa RLS forçada e concede ao papel de execução apenas o necessário."""
    runtime_role = os.getenv("APP_DATABASE_ROLE", "").strip()
    if runtime_role and not _ROLE_NAME.fullmatch(runtime_role):
        raise RuntimeError("APP_DATABASE_ROLE possui formato inválido.")

    predicate = (
        "(user_id = NULLIF(current_setting('finscope.user_id', true), '')::INTEGER)"
    )
    for table_name in _TENANT_TABLES:
        table = Base.metadata.tables[table_name]
        connection.execute(
            DDL("ALTER TABLE %(table)s ENABLE ROW LEVEL SECURITY").against(table)
        )
        connection.execute(
            DDL("ALTER TABLE %(table)s FORCE ROW LEVEL SECURITY").against(table)
        )
        connection.execute(
            DDL("DROP POLICY IF EXISTS tenant_isolation ON %(table)s").against(table)
        )
        connection.execute(
            DDL(
                "CREATE POLICY tenant_isolation ON %(table)s "
                f"USING {predicate} WITH CHECK {predicate}"
            ).against(table)
        )

    if runtime_role:
        # Identificadores não podem ser parâmetros SQL. O compositor do psycopg
        # aplica a citação correta após a validação estrita do nome do papel.
        role = pg_sql.Identifier(runtime_role)
        dbapi_connection = connection.connection.driver_connection
        with dbapi_connection.cursor() as cursor:
            cursor.execute(
                pg_sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE "
                    "ON ALL TABLES IN SCHEMA public TO {}"
                ).format(role)
            )
            cursor.execute(
                pg_sql.SQL(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(role)
            )


def _assert_runtime_postgres_security(connection) -> None:
    """Falha de modo seguro se o papel ou as tabelas puderem ignorar o RLS."""
    role = connection.execute(
        select(
            _PG_ROLES.c.rolname,
            _PG_ROLES.c.rolsuper,
            _PG_ROLES.c.rolbypassrls,
            _PG_ROLES.c.rolcreatedb,
            _PG_ROLES.c.rolcreaterole,
        ).where(_PG_ROLES.c.rolname == func.current_user())
    ).mappings().one_or_none()
    if (
        not role
        or role["rolsuper"]
        or role["rolbypassrls"]
        or role["rolcreatedb"]
        or role["rolcreaterole"]
    ):
        raise DatabaseSecurityError(
            "O papel PostgreSQL da aplicação possui privilégios administrativos."
        )

    privileged_membership = connection.execute(
        select(_PG_ROLES.c.rolname).where(
            (_PG_ROLES.c.rolsuper.is_(True) | _PG_ROLES.c.rolbypassrls.is_(True)),
            func.pg_has_role(func.current_user(), _PG_ROLES.c.oid, "MEMBER"),
        )
    ).mappings().first()
    if privileged_membership:
        raise DatabaseSecurityError(
            "O papel PostgreSQL da aplicação pertence a um papel que ignora RLS."
        )

    rows = connection.execute(
        select(
            _PG_CLASS.c.relname,
            _PG_CLASS.c.relrowsecurity,
            _PG_CLASS.c.relforcerowsecurity,
        )
        .join(_PG_NAMESPACE, _PG_NAMESPACE.c.oid == _PG_CLASS.c.relnamespace)
        .where(
            _PG_NAMESPACE.c.nspname == "public",
            _PG_CLASS.c.relname.in_(_TENANT_TABLES),
        )
    ).mappings().all()
    protected = {
        row["relname"]
        for row in rows
        if row["relrowsecurity"] and row["relforcerowsecurity"]
    }
    if set(_TENANT_TABLES) - protected:
        raise DatabaseSecurityError(
            "As políticas de isolamento PostgreSQL não estão completas."
        )


def _database_url() -> str:
    """Retorna a URL do banco configurado ou o SQLite local de contingência."""
    fallback = (Path(__file__).resolve().parents[1] / "finscope.db").as_posix()
    configured = os.getenv("DATABASE_URL", f"sqlite:///{fallback}")
    if configured.startswith("postgres://"):
        return configured.replace("postgres://", "postgresql+psycopg://", 1)
    if configured.startswith("postgresql://"):
        return configured.replace("postgresql://", "postgresql+psycopg://", 1)
    return configured


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _database_url().startswith("sqlite") else {},
)

_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"invalid-password", bcrypt.gensalt()).decode()


def _positive_env_int(name: str, default: int) -> int:
    """Lê um inteiro positivo do ambiente, usando um valor seguro como padrão."""
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _password_error(password: str) -> str | None:
    """Valida a política mínima de senha e retorna uma mensagem amigável."""
    if _CONTROL_CHARACTERS.search(password):
        return "A senha contém caracteres de controle não permitidos."
    if len(password.encode("utf-8")) > 72:
        return "A senha deve ocupar no máximo 72 bytes."
    if len(password) < 10:
        return "A senha precisa ter pelo menos 10 caracteres."
    if not any(char.islower() for char in password) or not any(char.isupper() for char in password):
        return "Use pelo menos uma letra maiúscula e uma minúscula."
    if not any(char.isdigit() for char in password):
        return "Inclua pelo menos um número na senha."
    return None


def _invite_error(invite_code: str | None) -> str | None:
    """Valida o convite configurado sem persistir ou registrar o segredo."""
    expected = os.getenv("BETA_INVITE_CODE", "").strip()
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if not expected:
        if environment == "production":
            return "O cadastro está temporariamente indisponível."
        return None
    submitted = (invite_code or "").strip()
    if len(submitted) > 256 or _CONTROL_CHARACTERS.search(submitted):
        return "Código de convite inválido."
    if not secrets.compare_digest(submitted, expected):
        return "Código de convite inválido."
    return None


def init_db() -> None:
    """Cria tabelas e aplica ajustes compatíveis com bancos de versões anteriores."""
    migrations_enabled = os.getenv("DATABASE_MIGRATIONS_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not migrations_enabled:
        with engine.connect() as connection:
            connection.execute(select(1))
            if engine.dialect.name == "postgresql":
                _assert_runtime_postgres_security(connection)
        return

    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    occurrence_columns = {
        column["name"] for column in inspector.get_columns("recurring_occurrences")
    }
    with engine.begin() as connection:
        if "email_verified" not in columns:
            connection.execute(
                DDL(
                    "ALTER TABLE %(table)s ADD COLUMN email_verified "
                    "BOOLEAN NOT NULL DEFAULT TRUE"
                ).against(User.__table__)
            )
        if "verified_at" not in columns:
            connection.execute(
                DDL(
                    "ALTER TABLE %(table)s ADD COLUMN verified_at TIMESTAMP NULL"
                ).against(User.__table__)
            )
        # A Beta 5.1 não bloqueia contas pela verificação de e-mail.
        connection.execute(update(User).values(email_verified=True))
        if "user_id" not in occurrence_columns:
            occurrence_table = RecurringOccurrence.__table__
            connection.execute(
                DDL(
                    "ALTER TABLE %(table)s ADD COLUMN user_id INTEGER"
                ).against(occurrence_table)
            )
            owner_id = (
                select(RecurringEntry.user_id)
                .where(RecurringEntry.id == RecurringOccurrence.recurring_entry_id)
                .scalar_subquery()
            )
            connection.execute(
                update(RecurringOccurrence)
                .where(RecurringOccurrence.user_id.is_(None))
                .values(user_id=owner_id)
            )
            if engine.dialect.name == "postgresql":
                connection.execute(
                    DDL(
                        "ALTER TABLE %(table)s ALTER COLUMN user_id SET NOT NULL"
                    ).against(occurrence_table)
                )
                connection.execute(
                    DDL(
                        "ALTER TABLE %(table)s "
                        "ADD CONSTRAINT fk_recurring_occurrences_user_id "
                        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                    ).against(occurrence_table)
                )
            user_id_index = next(
                index
                for index in occurrence_table.indexes
                if index.name == "ix_recurring_occurrences_user_id"
            )
            user_id_index.create(bind=connection, checkfirst=True)
        if engine.dialect.name == "postgresql":
            _configure_postgres_security(connection)


def create_user(
    name: str,
    email: str,
    password: str,
    invite_code: str | None = None,
) -> tuple[bool, str]:
    """Cria uma conta após validar convite, lista opcional e limite da beta."""
    try:
        normalized = _normalize_email(email)
        clean_name = _clean_plain_text(
            name,
            field="Nome",
            minimum=2,
            maximum=80,
        )
    except ValueError as error:
        return False, str(error)
    if password_error := _password_error(password):
        return False, password_error
    if invite_error := _invite_error(invite_code):
        return False, invite_error
    with Session(engine) as session:
        if engine.dialect.name == "postgresql":
            # Serializa somente o cadastro para que duas solicitações simultâneas
            # não ultrapassem o limite de participantes da beta.
            session.execute(select(func.pg_advisory_xact_lock(51002026)))
        if session.scalar(select(User).where(User.email == normalized)):
            return False, "Já existe uma conta com este e-mail."
        allowed = {
            item.strip().lower()
            for item in os.getenv("BETA_ALLOWED_EMAILS", "").split(",")
            if item.strip()
        }
        if allowed and normalized not in allowed:
            return False, "Este e-mail não está na lista de convidados da beta."
        max_users = _positive_env_int("BETA_MAX_USERS", 10)
        if (session.scalar(select(func.count(User.id))) or 0) >= max_users:
            return False, "A beta atingiu o limite de participantes."
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        now = utcnow()
        user = User(
                name=clean_name,
                email=normalized,
                password_hash=hashed,
                email_verified=True,
                verified_at=now,
            )
        session.add(user)
        session.flush()
        _set_rls_context(session, user.id)
        session.add(UserPreference(user_id=user.id, privacy_accepted_at=now))
        session.add(
            SecurityEvent(
                user_id=user.id,
                identity_hash=hashlib.sha256(normalized.encode()).hexdigest(),
                event_type="account_created",
            )
        )
        session.commit()
    return True, "Conta criada. Você já pode entrar no FinScope."


def authenticate(email: str, password: str) -> dict | None:
    """Autentica uma conta e aplica bloqueio progressivo contra tentativas repetidas."""
    try:
        normalized = _normalize_email(email)
    except ValueError:
        bcrypt.checkpw(b"invalid", _DUMMY_PASSWORD_HASH.encode())
        return None
    if _CONTROL_CHARACTERS.search(password) or len(password.encode("utf-8")) > 72:
        bcrypt.checkpw(b"invalid", _DUMMY_PASSWORD_HASH.encode())
        return None
    identity = hashlib.sha256(normalized.encode()).hexdigest()
    now = utcnow()
    with Session(engine) as session:
        throttle = session.scalar(select(LoginThrottle).where(LoginThrottle.email_hash == identity))
        if throttle and throttle.locked_until and throttle.locked_until > now:
            bcrypt.checkpw(password.encode(), _DUMMY_PASSWORD_HASH.encode())
            return None
        if throttle and throttle.locked_until:
            throttle.failed_attempts = 0
            throttle.locked_until = None

        user = session.scalar(
            select(User).where(User.email == normalized).with_for_update()
        )
        password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
        valid = bcrypt.checkpw(password.encode(), password_hash.encode())
        if not user or not valid:
            if not throttle:
                throttle = LoginThrottle(email_hash=identity, failed_attempts=0)
                session.add(throttle)
            throttle.failed_attempts += 1
            throttle.updated_at = now
            if throttle.failed_attempts >= _positive_env_int("LOGIN_MAX_ATTEMPTS", 5):
                lock_minutes = _positive_env_int("LOGIN_LOCK_MINUTES", 15)
                throttle.locked_until = now + timedelta(minutes=lock_minutes)
            session.add(
                SecurityEvent(
                    identity_hash=identity,
                    event_type="login_failed",
                    detail="Credenciais rejeitadas.",
                )
            )
            session.commit()
            return None
        if throttle:
            session.delete(throttle)
        session.add(
            SecurityEvent(
                user_id=user.id,
                identity_hash=identity,
                event_type="login_succeeded",
            )
        )
        session.commit()
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "email_verified": bool(user.email_verified),
        }


def issue_auth_token(email: str, purpose: str, ttl_minutes: int) -> tuple[str, str, str] | None:
    """Emite um token de uso único para recuperação ou verificação futura."""
    if purpose not in {"verify", "reset"}:
        raise ValueError("Finalidade de token inválida.")
    try:
        normalized = _normalize_email(email)
    except ValueError:
        return None
    now = utcnow()
    with Session(engine) as session:
        user = session.scalar(
            select(User).where(User.email == normalized).with_for_update()
        )
        if not user:
            return None
        recent = session.scalar(
            select(AuthToken).where(
                AuthToken.user_id == user.id,
                AuthToken.purpose == purpose,
                AuthToken.created_at > now - timedelta(seconds=60),
                AuthToken.used_at.is_(None),
            ).order_by(AuthToken.created_at.desc())
        )
        if recent:
            return None
        session.execute(
            update(AuthToken).where(
                AuthToken.user_id == user.id,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
            ).values(used_at=now)
        )
        raw = secrets.token_urlsafe(32)
        session.add(AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=ttl_minutes),
        ))
        session.commit()
        return raw, user.email, user.name


def verify_email_token(raw_token: str) -> tuple[bool, str]:
    """Valida um e-mail; reservado para uma versão beta futura."""
    if len(raw_token) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", raw_token):
        return False, "Este link de verificação é inválido ou expirou. Solicite um novo link."
    now = utcnow()
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    with Session(engine) as session:
        token = session.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == digest,
                AuthToken.purpose == "verify",
            ).with_for_update()
        )
        if not token or token.used_at or token.expires_at < now:
            return False, "Este link de verificação é inválido ou expirou. Solicite um novo link."
        user = session.get(User, token.user_id)
        if not user:
            return False, "Conta não encontrada."
        user.email_verified = True
        user.verified_at = now
        token.used_at = now
        session.commit()
        return True, "E-mail confirmado. Agora você pode entrar na sua conta."


def reset_password_token(raw_token: str, new_password: str) -> tuple[bool, str]:
    """Altera a senha quando o token de recuperação é válido e ainda não foi usado."""
    if password_error := _password_error(new_password):
        return False, password_error
    if len(raw_token) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", raw_token):
        return False, "Este link de recuperação é inválido ou expirou. Solicite um novo link."
    now = utcnow()
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    with Session(engine) as session:
        token = session.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == digest,
                AuthToken.purpose == "reset",
            ).with_for_update()
        )
        if not token or token.used_at or token.expires_at < now:
            return False, "Este link de recuperação é inválido ou expirou. Solicite um novo link."
        user = session.get(User, token.user_id)
        if not user:
            return False, "Conta não encontrada."
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        user.email_verified = True
        user.verified_at = user.verified_at or now
        token.used_at = now
        session.execute(
            update(AuthToken)
            .where(AuthToken.user_id == user.id, AuthToken.used_at.is_(None))
            .values(used_at=now)
        )
        session.commit()
        return True, "Senha alterada. Você já pode entrar com a nova senha."


def add_transaction(
    user_id: int,
    kind: str,
    amount: float,
    category: str,
    description: str,
    occurred_on: date,
) -> None:
    """Registra uma movimentação após validar todos os dados recebidos da interface."""
    clean_description = _clean_plain_text(
        description,
        field="Descrição",
        maximum=160,
    )
    if (
        kind not in TRANSACTION_CATEGORIES
        or category not in TRANSACTION_CATEGORIES[kind]
        or not 0 < amount < 1_000_000_000
        or len(clean_description) > 160
        or occurred_on > date.today()
    ):
        raise ValueError("Dados do lançamento inválidos.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.add(
            Transaction(
                user_id=user_id,
                kind=kind,
                amount=amount,
                category=category,
                description=clean_description,
                occurred_on=occurred_on,
            )
        )
        session.commit()


def transactions_frame(user_id: int, start_date: date | None = None) -> pd.DataFrame:
    """Retorna as movimentações da conta, com filtro inicial opcional."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        statement = select(Transaction).where(Transaction.user_id == user_id)
        if start_date:
            statement = statement.where(Transaction.occurred_on >= start_date)
        rows = (
            session.execute(
                statement.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
            )
            .scalars()
            .all()
        )
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Tipo": item.kind,
                "Valor": item.amount,
                "Categoria": item.category,
                "Descrição": item.description,
                "Data": item.occurred_on,
            }
            for item in rows
        ]
    )


def delete_transaction(user_id: int, transaction_id: int) -> None:
    """Exclui uma movimentação somente quando ela pertence à conta informada."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.execute(
            delete(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        session.commit()


def save_holding(user_id: int, ticker: str, quantity: float, avg_price: float) -> None:
    """Cria ou atualiza uma posição do portfólio virtual."""
    symbol = ticker.strip().upper().replace(".SA", "")
    if (
        not symbol
        or not re.fullmatch(r"(?:[A-Z0-9]{4}\d{1,2}|\^BVSP)", symbol)
        or not 0 < quantity < 1_000_000_000
        or not 0 < avg_price < 1_000_000_000
    ):
        raise ValueError("Dados da posição inválidos.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        holding = session.scalar(
            select(Holding).where(
                Holding.user_id == user_id,
                Holding.ticker == symbol,
            )
        )
        if holding:
            holding.quantity, holding.avg_price = quantity, avg_price
        else:
            session.add(
                Holding(
                    user_id=user_id,
                    ticker=symbol,
                    quantity=quantity,
                    avg_price=avg_price,
                )
            )
        session.commit()


def holdings_frame(user_id: int) -> pd.DataFrame:
    """Retorna as posições do portfólio pertencentes à conta informada."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        rows = (
            session.execute(
                select(Holding)
                .where(Holding.user_id == user_id)
                .order_by(Holding.ticker)
            )
            .scalars()
            .all()
        )
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Ativo": item.ticker,
                "Quantidade": item.quantity,
                "Preço médio": item.avg_price,
            }
            for item in rows
        ]
    )


def delete_holding(user_id: int, holding_id: int) -> None:
    """Exclui uma posição somente quando ela pertence à conta informada."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.execute(delete(Holding).where(Holding.id == holding_id, Holding.user_id == user_id))
        session.commit()


def user_summary(user_id: int, start_date: date | None = None) -> dict[str, float]:
    """Calcula receitas, despesas e saldo, com filtro inicial opcional."""
    frame = transactions_frame(user_id, start_date=start_date)
    if frame.empty:
        return {"income": 0.0, "expense": 0.0, "balance": 0.0}
    income = float(frame.loc[frame["Tipo"] == "Receita", "Valor"].sum())
    expense = float(frame.loc[frame["Tipo"] == "Despesa", "Valor"].sum())
    return {"income": income, "expense": expense, "balance": income - expense}


def get_dashboard(user_id: int) -> dict | None:
    """Obtém somente a configuração de dashboard pertencente à conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        dashboard = session.scalar(select(Dashboard).where(Dashboard.user_id == user_id))
        if not dashboard:
            return None
        return {
            "id": dashboard.id,
            "preferred_period": dashboard.preferred_period,
            "created_at": dashboard.created_at,
            "updated_at": dashboard.updated_at,
        }


def create_dashboard(user_id: int, preferred_period: int = 1) -> tuple[bool, str]:
    """Cria uma única dashboard para a conta autenticada."""
    if preferred_period not in DASHBOARD_PERIODS:
        return False, "Período inválido para a dashboard."
    try:
        with Session(engine) as session:
            _set_rls_context(session, user_id)
            if session.scalar(select(Dashboard).where(Dashboard.user_id == user_id)):
                return False, "Sua dashboard já foi criada."
            session.add(Dashboard(user_id=user_id, preferred_period=preferred_period))
            session.commit()
    except IntegrityError:
        return False, "Sua dashboard já foi criada."
    return True, "Dashboard criada com sucesso."


def update_dashboard_period(user_id: int, preferred_period: int) -> None:
    """Salva o período escolhido somente na dashboard da própria conta."""
    if preferred_period not in DASHBOARD_PERIODS:
        raise ValueError("Período inválido para a dashboard.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        dashboard = session.scalar(select(Dashboard).where(Dashboard.user_id == user_id))
        if not dashboard:
            raise ValueError("Dashboard não encontrada.")
        dashboard.preferred_period = preferred_period
        dashboard.updated_at = utcnow()
        session.commit()


def delete_dashboard(user_id: int) -> None:
    """Exclui a configuração visual sem apagar finanças ou investimentos."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.execute(delete(Dashboard).where(Dashboard.user_id == user_id))
        session.commit()


def authenticated_user(user_id: int) -> dict | None:
    """Recarrega a identidade confiável no servidor para uma sessão já autenticada."""
    try:
        safe_user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    with Session(engine) as session:
        user = session.get(User, safe_user_id)
        if not user:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "email_verified": bool(user.email_verified),
        }


def submit_feedback(
    user_id: int,
    category: str,
    message: str,
    rating: int | None = None,
    page: str = "",
) -> None:
    """Registra feedback da beta com validação de tamanho e valores permitidos."""
    clean_message = _clean_plain_text(
        message,
        field="Feedback",
        minimum=10,
        maximum=2_000,
    )
    clean_page = _clean_plain_text(page, field="Página", maximum=60)
    if category not in FEEDBACK_CATEGORIES:
        raise ValueError("Feedback inválido.")
    if rating is not None and rating not in range(0, 11):
        raise ValueError("A nota precisa estar entre 0 e 10.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.add(
            Feedback(
                user_id=user_id,
                category=category,
                rating=rating,
                page=clean_page,
                message=clean_message,
            )
        )
        session.commit()


def feedback_frame(user_id: int) -> pd.DataFrame:
    """Lista somente os feedbacks históricos pertencentes à própria conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        statement = (
            select(Feedback, User.name, User.email)
            .join(User, User.id == Feedback.user_id)
            .where(Feedback.user_id == user_id)
        )
        rows = session.execute(statement.order_by(Feedback.created_at.desc())).all()
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Usuário": name,
                "E-mail": email,
                "Categoria": item.category,
                "Nota": item.rating,
                "Página": item.page,
                "Mensagem": item.message,
                "Enviado em": item.created_at,
            }
            for item, name, email in rows
        ]
    )
def save_budget(user_id: int, category: str, monthly_limit: float) -> None:
    """Cria ou atualiza um teto mensal de despesas."""
    if category not in TRANSACTION_CATEGORIES["Despesa"] or not 0 < monthly_limit < 1_000_000_000:
        raise ValueError("Orçamento inválido.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        budget = session.scalar(
            select(Budget).where(Budget.user_id == user_id, Budget.category == category)
        )
        if budget:
            budget.monthly_limit = monthly_limit
            budget.updated_at = utcnow()
        else:
            session.add(Budget(user_id=user_id, category=category, monthly_limit=monthly_limit))
        session.commit()


def budgets_frame(user_id: int) -> pd.DataFrame:
    """Combina limites mensais com os gastos do mês corrente."""
    month_start = date.today().replace(day=1)
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        budgets = session.execute(
            select(Budget).where(Budget.user_id == user_id).order_by(Budget.category)
        ).scalars().all()
        totals = dict(
            session.execute(
                select(Transaction.category, func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.kind == "Despesa",
                    Transaction.occurred_on >= month_start,
                )
                .group_by(Transaction.category)
            ).all()
        )
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Categoria": item.category,
                "Limite": item.monthly_limit,
                "Gasto": float(totals.get(item.category, 0) or 0),
                "Disponível": item.monthly_limit - float(totals.get(item.category, 0) or 0),
            }
            for item in budgets
        ]
    )


def delete_budget(user_id: int, budget_id: int) -> None:
    """Remove um orçamento pertencente à conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.execute(delete(Budget).where(Budget.id == budget_id, Budget.user_id == user_id))
        session.commit()


def create_goal(
    user_id: int,
    name: str,
    target_amount: float,
    saved_amount: float = 0,
    deadline: date | None = None,
) -> None:
    """Cria uma meta financeira com valores positivos e nome curto."""
    clean_name = _clean_plain_text(
        name,
        field="Nome da meta",
        minimum=2,
        maximum=80,
    )
    if not 0 < target_amount < 1_000_000_000:
        raise ValueError("Meta inválida.")
    if not 0 <= saved_amount <= target_amount:
        raise ValueError("O valor guardado deve estar entre zero e o objetivo.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.add(
            SavingsGoal(
                user_id=user_id,
                name=clean_name,
                target_amount=target_amount,
                saved_amount=saved_amount,
                deadline=deadline,
            )
        )
        session.commit()


def goals_frame(user_id: int) -> pd.DataFrame:
    """Lista as metas financeiras da conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        rows = session.execute(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == user_id)
            .order_by(SavingsGoal.created_at.desc())
        ).scalars().all()
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Meta": item.name,
                "Objetivo": item.target_amount,
                "Guardado": item.saved_amount,
                "Progresso": min(item.saved_amount / item.target_amount, 1.0),
                "Prazo": item.deadline,
            }
            for item in rows
        ]
    )


def update_goal_amount(user_id: int, goal_id: int, saved_amount: float) -> None:
    """Atualiza o total guardado de uma meta da própria conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        goal = session.scalar(
            select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        if not goal or not 0 <= saved_amount <= goal.target_amount:
            raise ValueError("Valor da meta inválido.")
        goal.saved_amount = saved_amount
        goal.updated_at = utcnow()
        session.commit()


def delete_goal(user_id: int, goal_id: int) -> None:
    """Exclui uma meta pertencente à conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.execute(
            delete(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        session.commit()


def create_recurring_entry(
    user_id: int,
    kind: str,
    amount: float,
    category: str,
    description: str,
    day_of_month: int,
) -> None:
    """Salva uma previsão mensal sem criar movimentações automaticamente."""
    clean_description = _clean_plain_text(
        description,
        field="Descrição",
        maximum=160,
    )
    if (
        kind not in TRANSACTION_CATEGORIES
        or category not in TRANSACTION_CATEGORIES[kind]
        or not 0 < amount < 1_000_000_000
        or not 1 <= day_of_month <= 28
        or len(clean_description) > 160
    ):
        raise ValueError("Recorrência inválida.")
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        session.add(
            RecurringEntry(
                user_id=user_id,
                kind=kind,
                amount=amount,
                category=category,
                description=clean_description,
                day_of_month=day_of_month,
            )
        )
        session.commit()


def recurring_frame(user_id: int) -> pd.DataFrame:
    """Lista as previsões mensais ativas e inativas da conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        rows = session.execute(
            select(RecurringEntry)
            .where(RecurringEntry.user_id == user_id)
            .order_by(RecurringEntry.day_of_month, RecurringEntry.id)
        ).scalars().all()
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "Tipo": item.kind,
                "Valor": item.amount,
                "Categoria": item.category,
                "Descrição": item.description,
                "Dia": item.day_of_month,
                "Ativa": item.active,
            }
            for item in rows
        ]
    )


def confirm_recurring_entry(user_id: int, recurring_id: int, occurred_on: date) -> tuple[bool, str]:
    """Converte uma previsão em lançamento, impedindo duplicidade na mesma data."""
    if occurred_on > date.today():
        return False, "Uma previsão futura ainda não pode ser confirmada."
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        item = session.scalar(
            select(RecurringEntry).where(
                RecurringEntry.id == recurring_id,
                RecurringEntry.user_id == user_id,
                RecurringEntry.active.is_(True),
            )
        )
        if not item:
            return False, "Recorrência não encontrada."
        exists = session.scalar(
            select(RecurringOccurrence).where(
                RecurringOccurrence.user_id == user_id,
                RecurringOccurrence.recurring_entry_id == recurring_id,
                RecurringOccurrence.occurred_on == occurred_on,
            )
        )
        if exists:
            return False, "Esta recorrência já foi confirmada nessa data."
        transaction = Transaction(
            user_id=user_id,
            kind=item.kind,
            amount=item.amount,
            category=item.category,
            description=item.description,
            occurred_on=occurred_on,
        )
        session.add(transaction)
        session.flush()
        session.add(
            RecurringOccurrence(
                user_id=user_id,
                recurring_entry_id=item.id,
                transaction_id=transaction.id,
                occurred_on=occurred_on,
            )
        )
        session.commit()
    return True, "Lançamento recorrente confirmado."


def set_recurring_active(user_id: int, recurring_id: int, active: bool) -> None:
    """Ativa ou pausa uma recorrência pertencente à conta."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        item = session.scalar(
            select(RecurringEntry).where(
                RecurringEntry.id == recurring_id,
                RecurringEntry.user_id == user_id,
            )
        )
        if not item:
            raise ValueError("Recorrência não encontrada.")
        item.active = active
        session.commit()


def delete_recurring_entry(user_id: int, recurring_id: int) -> None:
    """Exclui uma recorrência; movimentações já confirmadas são mantidas."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        owned_entry = session.scalar(
            select(RecurringEntry.id).where(
                RecurringEntry.id == recurring_id,
                RecurringEntry.user_id == user_id,
            )
        )
        if owned_entry is None:
            raise ValueError("Recorrência não encontrada.")
        session.execute(
            delete(RecurringOccurrence).where(
                RecurringOccurrence.recurring_entry_id == recurring_id,
                RecurringOccurrence.user_id == user_id,
            )
        )
        session.execute(
            delete(RecurringEntry).where(
                RecurringEntry.id == recurring_id,
                RecurringEntry.user_id == user_id,
            )
        )
        session.commit()


def get_user_preference(user_id: int) -> dict[str, object]:
    """Obtém as preferências, criando os valores padrão quando necessário."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        preference = session.get(UserPreference, user_id)
        if not preference:
            preference = UserPreference(user_id=user_id)
            session.add(preference)
            session.commit()
        return {
            "weekly_summary_enabled": bool(preference.weekly_summary_enabled),
            "privacy_accepted_at": preference.privacy_accepted_at,
        }


def set_weekly_summary(user_id: int, enabled: bool) -> None:
    """Ativa ou desativa o resumo semanal por e-mail."""
    with Session(engine) as session:
        _set_rls_context(session, user_id)
        preference = session.get(UserPreference, user_id)
        if not preference:
            preference = UserPreference(user_id=user_id)
            session.add(preference)
        preference.weekly_summary_enabled = enabled
        preference.updated_at = utcnow()
        session.commit()


def weekly_summary_recipients() -> list[dict[str, object]]:
    """Retorna contas que aceitaram receber o resumo semanal."""
    start = date.today() - timedelta(days=6)
    with Session(engine) as session:
        users = session.execute(select(User).order_by(User.id)).scalars().all()
    return [
        {"id": user.id, "name": user.name, "email": user.email, "summary": user_summary(user.id, start)}
        for user in users
        if bool(get_user_preference(user.id)["weekly_summary_enabled"])
    ]


def delete_user_account(user_id: int) -> None:
    """Apaga permanentemente uma conta e seus dados pessoais dependentes."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return
        _set_rls_context(session, user_id)
        identity = hashlib.sha256(user.email.encode()).hexdigest()
        session.execute(
            delete(RecurringOccurrence).where(
                RecurringOccurrence.user_id == user_id
            )
        )
        for model in (
            AuthToken,
            Feedback,
            Budget,
            SavingsGoal,
            RecurringEntry,
            UserPreference,
            Dashboard,
            Holding,
            Transaction,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
        session.execute(
            delete(SecurityEvent).where(
                (SecurityEvent.user_id == user_id) | (SecurityEvent.identity_hash == identity)
            )
        )
        session.execute(delete(User).where(User.id == user_id))
        session.commit()
