import statistics
from typing import List, Optional

import requests

from src.models import RateData


BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
REQUEST_TIMEOUT = 15


def _do_post(
    url: str,
    payload: dict,
    timeout: int = REQUEST_TIMEOUT,
    max_retries: int = 2,
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < max_retries:
                continue
    raise RuntimeError(f"Binance P2P: fallaron {max_retries} intentos") from last_error


def _extract_valid_prices(ads: list) -> List[float]:
    prices: List[float] = []
    for ad in ads:
        adv = ad.get("adv", {})
        price_str = adv.get("price", "")
        if not price_str:
            continue
        try:
            price = float(price_str)
        except (ValueError, TypeError):
            continue
        if price <= 0:
            continue
        prices.append(price)
    return prices


def fetch_p2p_rate(
    asset: str = "USDT",
    fiat: str = "VES",
    trade_type: str = "SELL",
    rows: int = 10,
    pay_types: Optional[list] = None,
    aggregation: str = "median",
    merchant_check: bool = False,
    timeout: int = REQUEST_TIMEOUT,
    max_retries: int = 2,
) -> RateData:
    payload = {
        "page": 1,
        "rows": rows,
        "payTypes": pay_types or [],
        "asset": asset,
        "tradeType": trade_type,
        "fiat": fiat,
        "publisherType": None,
        "merchantCheck": merchant_check,
    }

    data = _do_post(BINANCE_P2P_URL, payload, timeout=timeout, max_retries=max_retries)

    ads = data.get("data", [])
    if not ads:
        raise ValueError("Binance P2P: no se encontraron anuncios")

    prices = _extract_valid_prices(ads)
    if not prices:
        raise ValueError("Binance P2P: no se pudieron extraer precios validos")

    if aggregation == "median":
        rate = statistics.median(prices)
    elif aggregation == "mean":
        rate = statistics.mean(prices)
    elif aggregation == "first":
        rate = prices[0]
    else:
        raise ValueError(f"Binance P2P: agregacion no soportada: {aggregation}")

    return RateData(
        promedio=round(float(rate), 2),
        fecha_actualizacion="",
        fuente="Binance P2P",
        nombre=f"{asset}/{fiat} ({trade_type})",
    )
