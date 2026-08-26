"""Exportação e importação segura dos dados pessoais do FinScope."""

from __future__ import annotations

import json
from datetime import date, datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from utils.database import (
    add_transaction,
    budgets_frame,
    feedback_frame,
    goals_frame,
    holdings_frame,
    recurring_frame,
    transactions_frame,
)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serializa CSV sem permitir que células textuais virem fórmulas."""
    safe_frame = frame.copy()
    for column in safe_frame.select_dtypes(include=["object", "string"]).columns:
        safe_frame[column] = safe_frame[column].map(
            lambda value: (
                "'" + value
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
            )
        )
    return safe_frame.to_csv(index=False).encode("utf-8-sig")


def build_account_export(user: dict[str, object]) -> bytes:
    """Cria um ZIP autocontido sem hashes de senha, tokens ou auditoria."""
    user_id = int(user["id"])
    account = {
        "nome": str(user["name"]),
        "email": str(user["email"]),
        "exportado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "aviso": "Este arquivo contém dados pessoais. Guarde-o em local seguro.",
    }
    datasets = {
        "lancamentos.csv": transactions_frame(user_id),
        "investimentos.csv": holdings_frame(user_id),
        "orcamentos.csv": budgets_frame(user_id),
        "metas.csv": goals_frame(user_id),
        "recorrencias.csv": recurring_frame(user_id),
        "feedback.csv": feedback_frame(user_id).drop(
            columns=["Usuário", "E-mail", "Nota interna"], errors="ignore"
        ),
    }
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "conta.json",
            json.dumps(account, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        archive.writestr(
            "LEIA-ME.txt",
            (
                "Exportação de dados do FinScope\n\n"
                "Os arquivos CSV podem ser abertos no Excel ou LibreOffice. "
                "A exportação não contém senha, código de convite nem tokens.\n"
            ).encode("utf-8"),
        )
        for filename, frame in datasets.items():
            archive.writestr(filename, _csv_bytes(frame))
    return output.getvalue()


def import_transactions_csv(user_id: int, content: bytes) -> tuple[int, list[str]]:
    """Importa até mil lançamentos, validando cada linha no domínio da aplicação."""
    if len(content) > 2_000_000:
        raise ValueError("O arquivo deve ter no máximo 2 MB.")
    try:
        frame = pd.read_csv(BytesIO(content), sep=None, engine="python")
    except Exception as exc:
        raise ValueError("Não foi possível ler o arquivo CSV.") from exc
    if len(frame) > 1_000:
        raise ValueError("O arquivo pode conter no máximo mil linhas.")
    aliases = {
        "tipo": "Tipo",
        "valor": "Valor",
        "categoria": "Categoria",
        "descrição": "Descrição",
        "descricao": "Descrição",
        "data": "Data",
    }
    frame = frame.rename(columns={column: aliases.get(str(column).strip().lower(), column) for column in frame})
    required = {"Tipo", "Valor", "Categoria", "Data"}
    if not required.issubset(frame.columns):
        raise ValueError("Use as colunas Tipo, Valor, Categoria e Data.")
    imported = 0
    errors: list[str] = []
    for index, row in frame.iterrows():
        try:
            raw_value = str(row["Valor"]).strip().replace("R$", "").replace(" ", "")
            if "," in raw_value:
                raw_value = raw_value.replace(".", "").replace(",", ".")
            occurred = pd.to_datetime(row["Data"], dayfirst=True, errors="raise").date()
            add_transaction(
                user_id=user_id,
                kind=str(row["Tipo"]).strip().title(),
                amount=float(raw_value),
                category=str(row["Categoria"]).strip(),
                description="" if pd.isna(row.get("Descrição", "")) else str(row.get("Descrição", "")),
                occurred_on=occurred,
            )
            imported += 1
        except Exception:
            errors.append(f"Linha {index + 2}: dados inválidos.")
    return imported, errors[:20]
