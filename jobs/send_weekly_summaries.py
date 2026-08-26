"""Tarefa agendada para envio dos resumos semanais autorizados."""

from utils.database import init_db, weekly_summary_recipients
from utils.email_service import send_weekly_summary_email


def main() -> int:
    """Envia um e-mail por destinatário e retorna erro se alguma entrega falhar."""
    init_db()
    failed = 0
    for recipient in weekly_summary_recipients():
        result = send_weekly_summary_email(
            str(recipient["email"]),
            str(recipient["name"]),
            recipient["summary"],
        )
        print(f"weekly_summary user_id={recipient['id']} sent={result.sent}")
        failed += int(not result.sent)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
