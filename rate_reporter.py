#!/usr/bin/env python3
"""Script diario de tasas BCV y Binance P2P.

Uso:
    python rate_reporter.py --config config.example.yaml
"""

import argparse
import logging
import sys
from typing import List

from src.adjustments import apply_adjustments
from src.callmebot import send_whatsapp_message
from src.config import AppConfig, load_config
from src.logger import setup_logger
from src.message import format_message
from src.models import RateResult
from src.providers import binance_p2p, dolarapi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reporter diario de tasas")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al archivo de configuracion YAML",
    )
    return parser.parse_args()


def fetch_rate(
    config: AppConfig,
    rate_key: str,
    logger: logging.Logger,
) -> RateResult:
    rate_cfg = config.get_rate_config(rate_key)
    if rate_cfg is None or not rate_cfg.enabled:
        logger.info(f"Tasa '{rate_key}' desactivada en configuracion")
        return RateResult(
            label=rate_cfg.label if rate_cfg else rate_key,
            provider_name="",
            base_rate=0,
            adjusted_rate=0,
            rule_description="",
            source="",
            updated_at="",
            available=False,
            error_message="Desactivada en configuracion",
        )

    timeout = config.request_timeout
    max_retries = config.max_retries

    try:
        provider = rate_cfg.provider

        if provider == "dolarapi_usd_official":
            data = dolarapi.fetch_usd_official(timeout=timeout, max_retries=max_retries)
        elif provider == "dolarapi_eur_official":
            data = dolarapi.fetch_eur_official(timeout=timeout, max_retries=max_retries)
        elif provider == "binance_p2p":
            bc = rate_cfg.binance
            data = binance_p2p.fetch_p2p_rate(
                asset=bc.asset if bc else "USDT",
                fiat=bc.fiat if bc else "VES",
                trade_type=bc.trade_type if bc else "SELL",
                rows=bc.rows if bc else 10,
                pay_types=bc.pay_types if bc else None,
                aggregation=bc.aggregation if bc else "median",
                merchant_check=bc.merchant_check if bc else False,
                timeout=timeout,
                max_retries=max_retries,
            )
        else:
            raise ValueError(f"Proveedor no soportado: {provider}")

        base_rate = data.promedio
        adj = rate_cfg.adjustments
        adjusted_rate, rule = apply_adjustments(
            base_rate=base_rate,
            percent_subtract=adj.percent_subtract,
            fixed_subtract_bs=adj.fixed_subtract_bs,
            round_decimals=config.round_decimals,
        )

        logger.info(f"{rate_cfg.label}: base={base_rate} ajustada={adjusted_rate}")

        return RateResult(
            label=rate_cfg.label,
            provider_name=provider,
            base_rate=base_rate,
            adjusted_rate=adjusted_rate,
            rule_description=rule,
            source=data.fuente,
            updated_at=data.fecha_actualizacion,
            available=True,
        )

    except Exception as e:
        logger.error(f"{rate_cfg.label}: error — {e}")

        if rate_cfg.fallback_manual_rate is not None:
            fallback = rate_cfg.fallback_manual_rate
            adj = rate_cfg.adjustments
            adjusted_rate, rule = apply_adjustments(
                base_rate=fallback,
                percent_subtract=adj.percent_subtract,
                fixed_subtract_bs=adj.fixed_subtract_bs,
                round_decimals=config.round_decimals,
            )
            logger.warning(f"{rate_cfg.label}: usando tasa manual de respaldo: {fallback}")
            return RateResult(
                label=rate_cfg.label,
                provider_name="fallback",
                base_rate=fallback,
                adjusted_rate=adjusted_rate,
                rule_description=rule,
                source="Manual",
                updated_at="",
                available=True,
            )

        return RateResult(
            label=rate_cfg.label,
            provider_name=rate_cfg.provider,
            base_rate=0,
            adjusted_rate=0,
            rule_description="",
            source="",
            updated_at="",
            available=False,
            error_message=str(e),
        )


def run(config_path: str) -> int:
    logger = setup_logger()
    logger.info("Iniciando reporter de tasas")

    config = load_config(config_path)

    rate_keys = ["bcv_usd", "bcv_eur", "binance_usdt"]
    results: List[RateResult] = []

    for key in rate_keys:
        rate_cfg = config.get_rate_config(key)
        if rate_cfg is None or not rate_cfg.enabled:
            continue
        result = fetch_rate(config, key, logger)
        results.append(result)

    message = format_message(results, timezone=config.timezone)

    if config.output.print_console:
        print(message)

    if config.output.save_to_file:
        try:
            with open(config.output.output_file, "w", encoding="utf-8") as f:
                f.write(message)
            logger.info(f"Mensaje guardado en {config.output.output_file}")
        except OSError as e:
            logger.error(f"Error al guardar archivo: {e}")

    if config.callmebot.enabled:
        success = send_whatsapp_message(message, config.callmebot, logger)
        if not success:
            logger.warning("WhatsApp fallo — mensaje guardado localmente como respaldo")

    available_count = sum(1 for r in results if r.available)
    if available_count == 0:
        logger.error("Ninguna tasa disponible. Revise los proveedores.")
        return 1

    logger.info(f"Reporter finalizado: {available_count}/{len(results)} tasas disponibles")
    return 0


def main() -> None:
    args = parse_args()
    exit_code = run(args.config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
