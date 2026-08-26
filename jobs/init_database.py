"""Executa migrações e políticas de segurança antes de iniciar a aplicação."""

from utils.database import init_db


if __name__ == "__main__":
    init_db()
    print("Banco de dados e políticas RLS atualizados com sucesso.")
