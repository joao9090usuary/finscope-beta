"""Funções de apresentação para o padrão numérico brasileiro."""

from __future__ import annotations

import math


def format_decimal(value: float, decimal_places: int = 2) -> str:
    """Formata um número com ponto para milhar e vírgula para decimais."""
    number = float(value)
    if not math.isfinite(number):
        return "—"
    formatted = f"{number:,.{decimal_places}f}"
    return formatted.translate(str.maketrans({",": ".", ".": ","}))


def format_brl(value: float) -> str:
    """Formata um valor monetário em reais, conforme o uso brasileiro."""
    formatted = format_decimal(value)
    return "—" if formatted == "—" else f"R$ {formatted}"


def format_percent(value: float, decimal_places: int = 1) -> str:
    """Formata um percentual com vírgula decimal."""
    formatted = format_decimal(value, decimal_places)
    return "—" if formatted == "—" else f"{formatted}%"
