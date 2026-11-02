#!/usr/bin/env python3
"""Carga en Odoo las tasas BCV USD, BCV EUR y Binance P2P (compra y venta).

- Registra una fila en el modelo x_tasa_cambio ("Tasas de cambio") con las 4 tasas.
- Escribe las tasas contables (res.currency.rate) en todas las empresas activas, sobrescribiendo la del mismo dia:
  - por defecto, BCV USD/EUR con fecha = fecha valor del BCV;
  - en las empresas de BINANCE_RATE_COMPANY_IDS, el bolivar a Binance compra con fecha = hoy (hora Venezuela);
    el EUR mantiene la relacion EUR/USD del BCV. La ultima ejecucion del dia deja la tasa del dia.

Variables de entorno: ODOO_BASE_URL, ODOO_DATABASE, ODOO_API_KEY, TIMEZONE (America/Caracas),
BINANCE_RATE_COMPANY_IDS (ids separados por coma; vacio = todas con BCV).
Uso: python odoo_sync.py [--dry-run]
"""

import argparse
import os
import sys
from datetime import date, datetime, timezone
from typing import Dict, Optional, Tuple

import pytz
from dotenv import load_dotenv

from src.logger import setup_logger
from src.odoo_client import OdooClient
from src.providers import bcv, binance_p2p

load_dotenv()

TIMEZONE = os.environ.get("TIMEZONE", "America/Caracas")
BCV_CURRENCY = "VEF"  # En esta base el bolivar es la moneda "VEF" (Bolivar Soberano)
ALL_COMPANIES_CONTEXT = {"active_test": False}
BINANCE_RATE_COMPANY_IDS = {int(x) for x in os.environ.get("BINANCE_RATE_COMPANY_IDS", "").split(",") if x.strip()}

logger = setup_logger("odoo_sync")


def company_rates(bs_per: Dict[str, float], company_currency: str) -> Dict[str, float]:
    """Tasa contable de cada moneda para una empresa: unidades de la moneda por 1 unidad de la moneda de la empresa."""
    base = bs_per[company_currency]
    return {name: base / value for name, value in bs_per.items() if name != company_currency}


def fetch_binance(trade_type: str) -> Optional[float]:
    try:
        return binance_p2p.fetch_p2p_rate(trade_type=trade_type, rows=10, aggregation="median").promedio
    except Exception as e:  # noqa: BLE001 - una tasa caida no debe impedir cargar las demas
        logger.error(f"Binance {trade_type}: {e}")
        return None


def rate_plan(company_id: int, bcv_rates: Optional[bcv.BcvRates], compra: Optional[float], today: date) -> Optional[Tuple[str, Dict[str, float]]]:
    """Fecha y Bs por unidad de cada moneda que se usan como tasa contable de la empresa (None si no hay tasa)."""
    if company_id in BINANCE_RATE_COMPANY_IDS:
        if not compra:
            return None
        bs_per = {BCV_CURRENCY: 1.0, "USD": compra}
        if bcv_rates:
            bs_per["EUR"] = compra * bcv_rates.eur / bcv_rates.usd  # EUR/USD del BCV
        return today.isoformat(), bs_per
    if not bcv_rates:
        return None
    return bcv_rates.fecha_valor.isoformat(), {BCV_CURRENCY: 1.0, "USD": bcv_rates.usd, "EUR": bcv_rates.eur}


def upsert_rates(odoo: OdooClient, bcv_rates: Optional[bcv.BcvRates], compra: Optional[float], today: date, dry_run: bool) -> list:
    notes = []
    currencies = {c["name"]: c["id"] for c in odoo.search_read("res.currency", [["name", "in", [BCV_CURRENCY, "USD", "EUR"]]], ["name"], ALL_COMPANIES_CONTEXT)}
    # Solo empresas activas: Odoo rechaza escribir con una empresa archivada en allowed_company_ids.
    companies = odoo.search_read("res.company", [["active", "=", True]], ["name", "currency_id"], ALL_COMPANIES_CONTEXT)

    for company in companies:
        company_currency = company["currency_id"][1]
        plan = rate_plan(company["id"], bcv_rates, compra, today)
        if plan is None:
            notes.append(f"{company['name']}: sin tasa ({'Binance' if company['id'] in BINANCE_RATE_COMPANY_IDS else 'BCV'} no disponible), se mantiene la anterior")
            continue
        day, bs_per = plan
        if company_currency not in bs_per:
            notes.append(f"{company['name']}: moneda {company_currency} no soportada, omitida")
            continue
        context = {"allowed_company_ids": [company["id"]], "active_test": False}
        for currency, value in company_rates(bs_per, company_currency).items():
            currency_id = currencies.get(currency)
            if not currency_id:
                notes.append(f"moneda {currency} no existe en Odoo")
                continue
            # En empresas a Binance, las tasas con fecha posterior (fecha valor BCV adelantada) tambien se igualan
            op = ">=" if company["id"] in BINANCE_RATE_COMPANY_IDS else "="
            existing = odoo.search_read(
                "res.currency.rate",
                [["currency_id", "=", currency_id], ["company_id", "=", company["id"]], ["name", op, day]],
                ["name", "company_rate"],
                context,
            )
            same_day = [r for r in existing if r["name"] == day]
            logger.info(f"{company['name']}: {'actualiza' if same_day else 'crea'} {currency} {day} = {value:.8f}")
            if dry_run:
                continue
            if existing:
                odoo.write("res.currency.rate", [r["id"] for r in existing], {"company_rate": value}, context)
            if not same_day:
                odoo.create("res.currency.rate", {"currency_id": currency_id, "company_id": company["id"], "name": day, "company_rate": value}, context)
    return notes


def run(dry_run: bool) -> int:
    odoo = OdooClient(os.environ["ODOO_BASE_URL"], os.environ["ODOO_DATABASE"], os.environ["ODOO_API_KEY"])
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(pytz.timezone(TIMEZONE))
    notes = []

    rates: Optional[bcv.BcvRates] = None
    try:
        rates = bcv.fetch_bcv_with_fallback()
        logger.info(f"BCV ({rates.fuente}): USD {rates.usd} EUR {rates.eur} fecha valor {rates.fecha_valor}")
        if rates.fuente != "bcv.org.ve":
            notes.append(rates.fuente)
    except Exception as e:  # noqa: BLE001
        logger.error(f"BCV: {e}")
        notes.append(f"BCV no disponible: {e}")

    compra = fetch_binance("BUY")
    venta = fetch_binance("SELL")
    logger.info(f"Binance P2P USDT/VES: compra {compra} venta {venta}")
    if compra is None or venta is None:
        notes.append("Binance P2P no disponible (ver log)")

    notes.extend(upsert_rates(odoo, rates, compra, now_local.date(), dry_run))

    row = {
        "x_name": now_local.strftime("%Y-%m-%d %H:%M"),
        "x_fecha_hora": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "x_fecha_valor_bcv": rates.fecha_valor.isoformat() if rates else False,
        "x_bcv_usd": rates.usd if rates else 0.0,
        "x_bcv_eur": rates.eur if rates else 0.0,
        "x_binance_compra": compra or 0.0,
        "x_binance_venta": venta or 0.0,
        "x_nota": "\n".join(notes) or False,
    }
    if dry_run:
        logger.info(f"[dry-run] fila x_tasa_cambio: {row}")
    else:
        row_id = odoo.create("x_tasa_cambio", row)
        logger.info(f"Fila x_tasa_cambio {row_id} creada")

    if rates is None and compra is None and venta is None:
        logger.error("Ninguna tasa disponible")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga las tasas BCV y Binance en Odoo")
    parser.add_argument("--dry-run", action="store_true", help="Consulta las tasas pero no escribe en Odoo")
    sys.exit(run(parser.parse_args().dry_run))


if __name__ == "__main__":
    main()
