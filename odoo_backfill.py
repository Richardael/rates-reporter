#!/usr/bin/env python3
"""Carga en Odoo las tasas BCV USD/EUR historicas (DolarAPI) entre dos fechas.

Por cada fecha valor publicada: tasas contables en todas las empresas (sobrescribe) y una fila
en x_tasa_cambio sin Binance (Binance P2P no tiene historico).
Uso: python odoo_backfill.py 2026-10-01 2026-10-29 [--dry-run]
"""

import argparse
import os
import sys
from datetime import date, datetime, time

import pytz
from dotenv import load_dotenv

from odoo_sync import TIMEZONE, upsert_rates
from src.logger import setup_logger
from src.odoo_client import OdooClient
from src.providers import dolarapi
from src.providers.bcv import BcvRates

load_dotenv()

logger = setup_logger("odoo_backfill")
NOTE = "Historico BCV via DolarAPI; Binance P2P sin historico"


def run(date_from: date, date_to: date, dry_run: bool) -> int:
    odoo = OdooClient(os.environ["ODOO_BASE_URL"], os.environ["ODOO_DATABASE"], os.environ["ODOO_API_KEY"])
    usd = dolarapi.fetch_official_history("dolares")
    eur = dolarapi.fetch_official_history("euros")
    days = sorted(d for d in usd if date_from.isoformat() <= d <= date_to.isoformat() and d in eur)
    if not days:
        logger.error("Sin fechas en el rango")
        return 1
    tz = pytz.timezone(TIMEZONE)
    existing = {
        r["x_fecha_valor_bcv"]
        for r in odoo.search_read("x_tasa_cambio", [["x_fecha_valor_bcv", "in", days]], ["x_fecha_valor_bcv"])
    }

    for day in days:
        rates = BcvRates(usd=usd[day], eur=eur[day], fecha_valor=date.fromisoformat(day), fuente="DolarAPI historico")
        logger.info(f"{day}: USD {rates.usd} EUR {rates.eur}")
        notes = upsert_rates(odoo, rates, dry_run)
        if day in existing:
            logger.info(f"{day}: ya hay fila en x_tasa_cambio, no se duplica")
            continue
        stamp = tz.localize(datetime.combine(rates.fecha_valor, time(9, 0))).astimezone(pytz.utc)
        row = {
            "x_name": f"{day} historico",
            "x_fecha_hora": stamp.strftime("%Y-%m-%d %H:%M:%S"),
            "x_fecha_valor_bcv": day,
            "x_bcv_usd": rates.usd,
            "x_bcv_eur": rates.eur,
            "x_nota": "\n".join([NOTE, *notes]),
        }
        if not dry_run:
            odoo.create("x_tasa_cambio", row)
    logger.info(f"{len(days)} fechas procesadas ({days[0]} a {days[-1]})")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga tasas BCV historicas en Odoo")
    parser.add_argument("date_from", type=date.fromisoformat)
    parser.add_argument("date_to", type=date.fromisoformat)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(args.date_from, args.date_to, args.dry_run))


if __name__ == "__main__":
    main()
