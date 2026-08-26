"""Cotações da B3 e indicadores técnicos com fonte identificada."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

_CACHE_DIR = Path(
    os.getenv(
        "YFINANCE_CACHE_DIR",
        Path(tempfile.gettempdir()) / "finscope-yfinance",
    )
)
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(_CACHE_DIR))

VALID_PERIODS = {"1mo", "3mo", "5d", "6mo", "1y", "2y"}
# Códigos à vista mais comuns da B3 têm quatro caracteres de base e um ou
# dois algarismos finais. O índice Ibovespa é consultado como ^BVSP.
TICKER_PATTERN = re.compile(r"^(?:[A-Z0-9]{4}\d{1,2}|\^BVSP)$")


class MarketDataError(RuntimeError):
    """Erro seguro, sem incluir token ou detalhes internos da requisição."""


def normalize_ticker(ticker: str) -> str:
    symbol = ticker.upper().replace(".SA", "").strip()
    if not TICKER_PATTERN.fullmatch(symbol):
        raise ValueError(
            "Informe um código de negociação da B3, como PETR4, BOVA11 ou ^BVSP."
        )
    return symbol


def _brapi_json(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    base_url = os.getenv("BRAPI_BASE_URL", "https://brapi.dev/api").rstrip("/")
    headers = {"Accept": "application/json", "User-Agent": "FinScope/1.0"}
    if token := os.getenv("BRAPI_TOKEN", "").strip():
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(
            f"{base_url}/{endpoint.lstrip('/')}",
            params=params,
            headers=headers,
            timeout=12,
        )
    except requests.RequestException as exc:
        raise MarketDataError("A brapi.dev não respondeu a tempo.") from exc
    if response.status_code == 429:
        raise MarketDataError("O limite temporário da brapi.dev foi atingido.")
    if response.status_code in {401, 403}:
        raise MarketDataError("O token da brapi.dev não permite consultar este ativo.")
    if not response.ok:
        raise MarketDataError("A brapi.dev não conseguiu consultar este ativo.")
    try:
        return response.json()
    except ValueError as exc:
        raise MarketDataError("A brapi.dev retornou uma resposta inválida.") from exc


def parse_brapi_history(payload: dict[str, Any]) -> pd.DataFrame:
    """Converte a resposta v2 da brapi em OHLCV; separado para testes."""
    try:
        result = payload["results"][0]
        data = result["data"]
        points = data["historicalDataPrice"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MarketDataError("A brapi.dev não retornou histórico para este ativo.") from exc
    if not points:
        raise MarketDataError("A brapi.dev não retornou histórico para este período.")

    frame = pd.DataFrame(points)
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise MarketDataError("O histórico recebido está incompleto.")
    adjusted = frame["adjustedClose"] if "adjustedClose" in frame else frame["close"]
    output = pd.DataFrame({
        "Date": pd.to_datetime(frame["date"], unit="s", utc=True).dt.tz_convert(None),
        "Open": pd.to_numeric(frame["open"], errors="coerce"),
        "High": pd.to_numeric(frame["high"], errors="coerce"),
        "Low": pd.to_numeric(frame["low"], errors="coerce"),
        "Close": pd.to_numeric(adjusted.fillna(frame["close"]), errors="coerce"),
        "Volume": pd.to_numeric(frame["volume"], errors="coerce").fillna(0),
    })
    output = output.dropna(subset=["Date", "Close"]).sort_values("Date").drop_duplicates("Date")
    if output.empty:
        raise MarketDataError("O histórico recebido não contém preços válidos.")
    return output.reset_index(drop=True)


def _brapi_history(ticker: str, period: str) -> pd.DataFrame:
    payload = _brapi_json(
        "v2/stocks/historical",
        {"symbols": ticker, "range": period, "interval": "1d", "sortOrder": "asc"},
    )
    return parse_brapi_history(payload)


def _yahoo_history(ticker: str, period: str) -> pd.DataFrame:
    symbol = ticker if ticker.endswith(".SA") or ticker.startswith("^") else f"{ticker}.SA"
    try:
        frame = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    except Exception as exc:
        raise MarketDataError("A fonte de contingência não respondeu.") from exc
    if frame.empty:
        raise MarketDataError("Nenhuma fonte retornou preços para este ativo.")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.reset_index()
    frame = frame.rename(columns={frame.columns[0]: "Date"})
    expected = ["Date", "Open", "High", "Low", "Close", "Volume"]
    if not set(expected).issubset(frame.columns):
        raise MarketDataError("A fonte de contingência retornou dados incompletos.")
    return frame[expected].dropna(subset=["Close"]).reset_index(drop=True)


def _demo_history(ticker: str, period: str) -> pd.DataFrame:
    days = {"5d": 5, "1mo": 22, "3mo": 66, "6mo": 132, "1y": 252, "2y": 504}.get(period, 132)
    rng = np.random.default_rng(sum(ord(char) for char in ticker))
    close = 35 * np.exp(np.cumsum(rng.normal(0.0005, 0.018, days)))
    frame = pd.DataFrame({"Date": pd.bdate_range(end=pd.Timestamp.today(), periods=days)})
    frame["Close"] = close
    frame["Open"] = close * (1 + rng.normal(0, 0.006, days))
    frame["High"] = np.maximum(frame["Open"], close) * (1 + rng.uniform(0.002, 0.018, days))
    frame["Low"] = np.minimum(frame["Open"], close) * (1 - rng.uniform(0.002, 0.018, days))
    frame["Volume"] = rng.integers(8_000_000, 42_000_000, days)
    return frame


def _indicators(frame: pd.DataFrame, source: str, demo: bool) -> pd.DataFrame:
    frame = frame.copy()
    close = frame["Close"]
    frame["MM20"] = close.rolling(20).mean()
    frame["MM50"] = close.rolling(50).mean()
    delta = close.diff()
    average_gain = delta.clip(lower=0).rolling(14).mean()
    average_loss = -delta.clip(upper=0).rolling(14).mean()
    ratio = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + ratio)
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_loss == 0) & (average_gain == 0), 50)
    frame["RSI"] = rsi
    frame["MACD"] = (
        close.ewm(span=12, adjust=False).mean()
        - close.ewm(span=26, adjust=False).mean()
    )
    frame["Sinal"] = frame["MACD"].ewm(span=9, adjust=False).mean()
    frame["Fonte"] = source
    frame["Demonstração"] = demo
    return frame.reset_index(drop=True)


@st.cache_data(ttl="1m", max_entries=80, show_spinner=False)
def prices(ticker: str, period: str = "6mo") -> pd.DataFrame:
    symbol = normalize_ticker(ticker)
    if period not in VALID_PERIODS:
        raise ValueError("Período de consulta inválido.")
    try:
        return _indicators(_brapi_history(symbol, period), "brapi.dev", False)
    except MarketDataError:
        try:
            return _indicators(
                _yahoo_history(symbol, period),
                "Yahoo Finance (contingência)",
                False,
            )
        except MarketDataError:
            return _indicators(_demo_history(symbol, period), "Demonstração local", True)


def parse_brapi_quote(payload: dict[str, Any]) -> dict[str, Any]:
    """Extrai o snapshot v2 da brapi; separado para testes."""
    try:
        data = payload["results"][0]["data"]
        price = float(data["regularMarketPrice"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MarketDataError("A brapi.dev não retornou uma cotação válida.") from exc
    previous = data.get("regularMarketPreviousClose")
    change_percent = data.get("regularMarketChangePercent")
    return {
        "price": price,
        "previous_close": float(previous) if previous is not None else None,
        "change_percent": float(change_percent) if change_percent is not None else None,
        "volume": float(data.get("regularMarketVolume") or 0),
        "updated_at": data.get("regularMarketTime"),
        "source": "brapi.dev",
        "demo": False,
    }


@st.cache_data(ttl="1m", max_entries=80, show_spinner=False)
def quote(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    try:
        payload = _brapi_json("v2/stocks/quote", {"symbols": symbol})
        return parse_brapi_quote(payload)
    except MarketDataError:
        history = prices(symbol, "5d")
        last = float(history["Close"].iloc[-1])
        previous = float(history["Close"].iloc[-2]) if len(history) > 1 else last
        return {
            "price": last,
            "previous_close": previous,
            "change_percent": ((last / previous) - 1) * 100 if previous else None,
            "volume": float(history["Volume"].iloc[-1]),
            "updated_at": pd.Timestamp(history["Date"].iloc[-1]).isoformat(),
            "source": str(history["Fonte"].iloc[-1]),
            "demo": bool(history["Demonstração"].iloc[-1]),
        }


def latest_price(ticker: str) -> float:
    return float(quote(ticker)["price"])
