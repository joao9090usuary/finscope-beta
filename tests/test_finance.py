"""Testes de interpretação das respostas da API financeira."""

import unittest

from utils.finance import normalize_ticker, parse_brapi_history, parse_brapi_quote


class FinanceTest(unittest.TestCase):
    """Valida os formatos de histórico e cotação utilizados pelo FinScope."""

    def test_brapi_v2_history_uses_adjusted_close(self) -> None:
        """O histórico deve priorizar o fechamento ajustado quando disponível."""
        payload = {
            "results": [
                {
                    "data": {
                        "historicalDataPrice": [
                            {
                                "date": 1_781_233_200,
                                "open": 41.06,
                                "high": 41.53,
                                "low": 40.82,
                                "close": 42.00,
                                "volume": 34_081_000,
                                "adjustedClose": 41.18,
                            }
                        ]
                    }
                }
            ]
        }

        frame = parse_brapi_history(payload)

        self.assertEqual(float(frame.iloc[0]["Close"]), 41.18)
        self.assertEqual(float(frame.iloc[0]["Volume"]), 34_081_000)

    def test_brapi_v2_quote_is_parsed(self) -> None:
        """A cotação deve manter preço, variação, volume, horário e origem."""
        payload = {
            "results": [
                {
                    "data": {
                        "regularMarketPrice": 44.30,
                        "regularMarketPreviousClose": 44.24,
                        "regularMarketChangePercent": 0.14,
                        "regularMarketVolume": 52_657_800,
                        "regularMarketTime": "2026-08-21T21:31:30.000Z",
                    }
                }
            ]
        }

        result = parse_brapi_quote(payload)

        self.assertEqual(result["source"], "brapi.dev")
        self.assertAlmostEqual(result["price"], 44.30)
        self.assertFalse(result["demo"])

    def test_only_b3_style_tickers_are_accepted(self) -> None:
        """Textos genéricos não devem gerar uma cotação demonstrativa."""
        self.assertEqual(normalize_ticker("petr4.sa"), "PETR4")
        self.assertEqual(normalize_ticker("^bvsp"), "^BVSP")
        with self.assertRaisesRegex(ValueError, "negociação da B3"):
            normalize_ticker("BITCOIN")


if __name__ == "__main__":
    unittest.main()
