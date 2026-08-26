"""Testes de autenticação e limites persistidos da Beta 5.1."""

import os
import unittest
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BETA_MAX_USERS"] = "10"
os.environ["BETA_INVITE_CODE"] = "convite-seguro-de-teste"
os.environ["APP_ENV"] = "development"
os.environ.pop("SMTP_HOST", None)

from utils.database import (  # noqa: E402
    authenticate,
    create_user,
    init_db,
    issue_auth_token,
    reset_password_token,
)
from utils.email_service import (  # noqa: E402
    _send_brevo_api,
    send_feedback_email,
    send_password_reset_email,
)


class AuthFlowTest(unittest.TestCase):
    """Valida cadastro sem verificação, recuperação e proteção de cota."""

    @classmethod
    def setUpClass(cls) -> None:
        """Inicializa o banco em memória uma vez para esta classe de testes."""
        init_db()

    def test_signup_allows_immediate_login_without_email_verification(self) -> None:
        """Uma conta nova deve entrar imediatamente na Beta 5.1."""
        ok, message = create_user(
            "Pessoa Beta",
            "beta@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )

        self.assertTrue(ok)
        self.assertIn("já pode entrar", message)
        user = authenticate("beta@example.com", "SenhaInicial123")
        self.assertIsNotNone(user)
        self.assertTrue(user["email_verified"])

    def test_password_reset_uses_a_single_use_token(self) -> None:
        """O token deve alterar a senha uma vez e tornar-se inválido em seguida."""
        ok, _ = create_user(
            "Pessoa Recuperação",
            "recuperacao@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        self.assertTrue(ok)

        reset, _, _ = issue_auth_token("recuperacao@example.com", "reset", 30)
        changed, _ = reset_password_token(reset, "NovaSenha456")

        self.assertTrue(changed)
        self.assertIsNone(authenticate("recuperacao@example.com", "SenhaInicial123"))
        self.assertIsNotNone(authenticate("recuperacao@example.com", "NovaSenha456"))
        self.assertFalse(reset_password_token(reset, "OutraSenha789")[0])

    def test_development_delivery_returns_safe_reset_link(self) -> None:
        """Sem SMTP, o desenvolvimento deve fornecer somente o link de recuperação."""
        ok, _ = create_user(
            "Outra Pessoa",
            "outra@example.com",
            "SenhaInicial123",
            "convite-seguro-de-teste",
        )
        self.assertTrue(ok)

        result = send_password_reset_email("outra@example.com")

        self.assertFalse(result.sent)
        self.assertTrue(result.debug_link.startswith("http://localhost:8501/?reset="))

    def test_signup_rejects_an_invalid_invite_code(self) -> None:
        """Um código incorreto não deve criar nem consumir uma vaga da beta."""
        ok, message = create_user(
            "Pessoa sem convite",
            "sem-convite@example.com",
            "SenhaInicial123",
            "convite-incorreto",
        )

        self.assertFalse(ok)
        self.assertEqual(message, "Código de convite inválido.")
        self.assertIsNone(authenticate("sem-convite@example.com", "SenhaInicial123"))

    @patch("utils.email_service._send_email")
    def test_feedback_is_sent_to_private_recipient(self, send_email) -> None:
        """O comentário deve usar o destino do ambiente e bloquear marcação ativa."""
        with patch.dict(
            os.environ,
            {"FEEDBACK_TO_EMAIL": "responsavel@example.com"},
        ):
            result = send_feedback_email(
                "participante@example.com",
                "Pessoa Beta",
                "Gostaria de sugerir um novo filtro mensal.",
            )
            self.assertTrue(result.sent)
            self.assertEqual(send_email.call_args.args[0], "responsavel@example.com")
            with self.assertRaises(ValueError):
                send_feedback_email(
                    "participante@example.com",
                    "Pessoa Beta",
                    "<script>alert('xss')</script>",
                )

    @patch("utils.email_service.requests.post")
    def test_brevo_delivery_uses_https_without_exposing_key_in_payload(self, post) -> None:
        """A credencial da Brevo deve seguir apenas no cabeçalho HTTPS."""
        post.return_value.status_code = 201
        with patch.dict(
            os.environ,
            {
                "BREVO_API_KEY": "chave-brevo-de-teste",
                "EMAIL_FROM": "FinScope <responsavel@example.com>",
            },
        ):
            _send_brevo_api(
                "participante@example.com",
                "Teste do FinScope",
                "Mensagem transacional de teste.",
            )

        url = post.call_args.args[0]
        request = post.call_args.kwargs
        self.assertEqual(url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request["headers"]["api-key"], "chave-brevo-de-teste")
        self.assertNotIn("chave-brevo-de-teste", str(request["json"]))
        self.assertEqual(request["json"]["to"][0]["email"], "participante@example.com")

    def test_production_fails_closed_without_an_invite_configuration(self) -> None:
        """Produção sem segredo deve manter novos cadastros bloqueados."""
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "BETA_INVITE_CODE": ""},
        ):
            ok, message = create_user(
                "Pessoa Bloqueada",
                "bloqueada@example.com",
                "SenhaInicial123",
            )

        self.assertFalse(ok)
        self.assertEqual(message, "O cadastro está temporariamente indisponível.")

if __name__ == "__main__":
    unittest.main()
