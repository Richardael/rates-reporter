from datetime import datetime
from typing import List

import pytz

from src.models import RateResult


def _format_rate_block(result: RateResult) -> str:
    if not result.available:
        return (
            f"{result.label}\n"
            f"Estado: No disponible\n"
            f"Motivo: {result.error_message or 'Error desconocido'}\n"
        )

    return (
        f"{result.label}\n"
        f"Base: {result.base_rate:,.2f} Bs\n"
        f"Ajustada: {result.adjusted_rate:,.2f} Bs\n"
    )


def format_message(results: List[RateResult], timezone: str = "America/Caracas") -> str:
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%I:%M %p")

    blocks = [f"=== TASAS DEL DIA — {date_str} * {time_str} ===\n"]

    for r in results:
        blocks.append(_format_rate_block(r))

    blocks.append("Fuente:")
    blocks.append("- BCV USD/EUR: DolarAPI / BCV")
    blocks.append("- Binance: Binance P2P")
    blocks.append("\nNota: tasas referenciales sujetas a disponibilidad de proveedores.")

    return "\n".join(blocks)
