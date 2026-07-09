from datetime import datetime

import pytz

from src.message import format_message
from src.models import RateResult


def _valid_result(**kwargs) -> RateResult:
    defaults = dict(
        label="BCV USD",
        provider_name="dolarapi",
        base_rate=674.93,
        adjusted_rate=674.93,
        rule_description="Sin ajuste",
        source="BCV",
        updated_at="2026-07-07",
        available=True,
    )
    defaults.update(kwargs)
    return RateResult(**defaults)


def _unavailable_result(label="Binance USDT", error="Error de conexion") -> RateResult:
    return RateResult(
        label=label,
        provider_name="binance_p2p",
        base_rate=0,
        adjusted_rate=0,
        rule_description="",
        source="",
        updated_at="",
        available=False,
        error_message=error,
    )


class TestFormatMessage:
    def test_all_available(self):
        results = [
            _valid_result(label="BCV USD", base_rate=674.93, adjusted_rate=674.93),
            _valid_result(label="BCV EUR", base_rate=770.68, adjusted_rate=770.68),
            _valid_result(label="Binance USDT", base_rate=780.00, adjusted_rate=768.44, rule_description="-0.2% y -10.00 Bs"),
        ]
        msg = format_message(results, timezone="America/Caracas")

        assert "=== TASAS DEL DIA" in msg
        assert "BCV USD" in msg
        assert "674.93" in msg
        assert "BCV EUR" in msg
        assert "770.68" in msg
        assert "Binance USDT" in msg
        assert "780.00" in msg
        assert "768.44" in msg
        assert "Fuente:" in msg
        assert "No disponible" not in msg

    def test_binance_unavailable_message_includes_error(self):
        results = [
            _valid_result(label="BCV USD", base_rate=674.93, adjusted_rate=674.93),
            _valid_result(label="BCV EUR", base_rate=770.68, adjusted_rate=770.68),
            _unavailable_result(label="Binance USDT", error="Timeout"),
        ]
        msg = format_message(results)

        assert "BCV USD" in msg
        assert "BCV EUR" in msg
        assert "Binance USDT" in msg
        assert "No disponible" in msg
        assert "Timeout" in msg

    def test_message_includes_date_and_time(self):
        results = [_valid_result()]
        msg = format_message(results, timezone="America/Caracas")

        tz = pytz.timezone("America/Caracas")
        now = datetime.now(tz)
        date_str = now.strftime("%d/%m/%Y")

        assert date_str in msg
