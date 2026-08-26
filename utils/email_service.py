"""Entrega de e-mails de autenticação.

Na Beta 5.2, a recuperação de senha e o resumo semanal são usados. O envio de
verificação fica isolado em :func:`send_verification_email` para uma versão
futura, sem interferir no cadastro ou no login atuais.
"""

from __future__ import annotations

import os
import re
import smtplib
import ssl
import unicodedata
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import urlencode

from utils.database import issue_auth_token


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_MARKUP = re.compile(r"<[^>]{0,512}>")


@dataclass(frozen=True)
class DeliveryResult:
    """Resultado seguro de uma tentativa de envio por e-mail."""

    sent: bool
    message: str
    debug_link: str | None = None


def _as_bool(name: str, default: bool = False) -> bool:
    """Converte uma variável de ambiente textual em valor booleano."""
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _send_smtp(recipient: str, subject: str, body: str) -> None:
    """Envia uma mensagem SMTP usando apenas configurações do ambiente."""
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        raise RuntimeError("SMTP não configurado")
    unsafe_production_hosts = {"mailpit", "localhost", "127.0.0.1"}
    if (
        os.getenv("APP_ENV", "development") == "production"
        and host.lower() in unsafe_production_hosts
    ):
        raise RuntimeError("SMTP real obrigatório em produção")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.getenv("EMAIL_FROM", "FinScope <no-reply@finscope.local>")
    message["To"] = recipient
    message.set_content(body)
    if _as_bool("SMTP_USE_SSL"):
        client = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(host, port, timeout=15)
    try:
        if _as_bool("SMTP_USE_TLS"):
            client.starttls(context=ssl.create_default_context())
        if username:
            client.login(username, password)
        client.send_message(message)
    finally:
        client.quit()


def _send_auth_email(email: str, purpose: str) -> DeliveryResult:
    """Monta e envia uma mensagem de autenticação de uso único."""
    ttl = 24 * 60 if purpose == "verify" else 30
    issued = issue_auth_token(email, purpose, ttl)
    if not issued:
        return DeliveryResult(
            False,
            "Se a conta existir, aguarde um minuto antes de solicitar outro link.",
        )
    raw, recipient, name = issued
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")
    parameter = "verify" if purpose == "verify" else "reset"
    link = f"{base_url}/?{urlencode({parameter: raw})}"
    if purpose == "verify":
        subject = "Confirme seu e-mail no FinScope"
        body = (
            f"Olá, {name}!\n\n"
            f"Confirme seu e-mail acessando o link abaixo:\n{link}\n\n"
            "O link expira em 24 horas e pode ser usado uma única vez."
        )
    else:
        subject = "Redefina sua senha do FinScope"
        body = (
            f"Olá, {name}!\n\n"
            f"Redefina sua senha acessando o link abaixo:\n{link}\n\n"
            "O link expira em 30 minutos e pode ser usado uma única vez. "
            "Se você não fez a solicitação, ignore esta mensagem."
        )
    try:
        _send_smtp(recipient, subject, body)
        return DeliveryResult(True, "E-mail enviado. Verifique também a pasta de spam.")
    except Exception:
        if os.getenv("APP_ENV", "development") != "production":
            return DeliveryResult(
                False,
                "Modo de desenvolvimento: use o link abaixo.",
                debug_link=link,
            )
        return DeliveryResult(
            False,
            "Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
        )


def send_password_reset_email(email: str) -> DeliveryResult:
    """Envia o link de recuperação de senha usado pela Beta 5.1."""
    return _send_auth_email(email, "reset")


def send_feedback_email(sender_email: str, sender_name: str, comment: str) -> DeliveryResult:
    """Envia texto simples ao endereço privado configurado para a beta."""
    recipient = os.getenv("FEEDBACK_TO_EMAIL", "").strip().lower()
    safe_sender = unicodedata.normalize("NFKC", sender_email).strip().lower()
    safe_name = " ".join(unicodedata.normalize("NFKC", sender_name).strip().split())
    safe_comment = unicodedata.normalize("NFKC", comment).strip()
    if not recipient or not _EMAIL_PATTERN.fullmatch(recipient):
        return DeliveryResult(False, "O recebimento de comentários ainda não foi configurado.")
    if not _EMAIL_PATTERN.fullmatch(safe_sender):
        raise ValueError("A conta autenticada possui um e-mail inválido.")
    if (
        not 2 <= len(safe_name) <= 80
        or _CONTROL_CHARACTERS.search(safe_name)
        or _HTML_MARKUP.search(safe_name)
    ):
        raise ValueError("O nome da conta contém caracteres não permitidos.")
    if (
        not 10 <= len(safe_comment) <= 2_000
        or _CONTROL_CHARACTERS.search(safe_comment)
        or _HTML_MARKUP.search(safe_comment)
    ):
        raise ValueError("Escreva um comentário entre 10 e 2.000 caracteres, sem marcação HTML.")

    body = (
        "Novo comentário recebido pelo FinScope Beta\n\n"
        f"Participante: {safe_name}\n"
        f"E-mail para resposta: {safe_sender}\n\n"
        "Comentário:\n"
        f"{safe_comment}\n"
    )
    try:
        _send_smtp(recipient, "Novo comentário do FinScope Beta", body)
        return DeliveryResult(True, "Comentário enviado com sucesso.")
    except Exception:
        return DeliveryResult(
            False,
            "Não foi possível enviar o comentário agora. Tente novamente mais tarde.",
        )


def send_verification_email(email: str) -> DeliveryResult:
    """Envia uma verificação de e-mail reservada para uma versão beta futura."""
    return _send_auth_email(email, "verify")


def send_weekly_summary_email(
    email: str,
    name: str,
    summary: dict[str, float],
) -> DeliveryResult:
    """Envia um resumo agregado dos últimos sete dias, sem detalhar lançamentos."""
    def money(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    subject = "Seu resumo semanal do FinScope"
    body = (
        f"Olá, {name}!\n\n"
        "Este é o resumo dos últimos sete dias no FinScope:\n"
        f"- Receitas: {money(summary['income'])}\n"
        f"- Despesas: {money(summary['expense'])}\n"
        f"- Saldo: {money(summary['balance'])}\n\n"
        "Acesse o FinScope para consultar os detalhes. Você pode desativar este "
        "e-mail em Minha conta.\n\n"
        "Mensagem automática da beta fechada do FinScope."
    )
    try:
        _send_smtp(email, subject, body)
        return DeliveryResult(True, "Resumo semanal enviado.")
    except Exception:
        return DeliveryResult(
            False,
            "Não foi possível enviar o resumo agora. Verifique a configuração SMTP.",
        )
