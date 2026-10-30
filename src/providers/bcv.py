import html
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

import certifi
import requests

from src.providers import dolarapi


BCV_URL = "https://www.bcv.org.ve/"
REQUEST_TIMEOUT = 25
# bcv.org.ve no envia su certificado intermedio correcto (manda uno de otra cadena), asi que
# se verifica con los raices de certifi + el intermedio Sectigo DV R36 publicado por Sectigo.
INTERMEDIATE = Path(__file__).resolve().parents[2] / "certs" / "sectigo-public-server-authentication-ca-dv-r36.pem"


@lru_cache(maxsize=1)
def _ca_bundle() -> str:
    bundle = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    bundle.write(Path(certifi.where()).read_text() + "\n" + INTERMEDIATE.read_text())
    bundle.close()
    return bundle.name

_RATE_RE = r'id="{id}".*?<strong[^>]*>\s*([\d.,]+)\s*</strong>'
_DATE_RE = re.compile(r'Fecha Valor:.*?content="(\d{4}-\d{2}-\d{2})', re.S)


@dataclass
class BcvRates:
    usd: float
    eur: float
    fecha_valor: date
    fuente: str


def _to_float(value: str) -> float:
    # El BCV publica "889,25530000": punto de miles opcional, coma decimal.
    return float(value.replace(".", "").replace(",", "."))


def parse_bcv_html(page: str) -> BcvRates:
    rates = {}
    for key in ("dolar", "euro"):
        match = re.search(_RATE_RE.format(id=key), page, re.S)
        if not match:
            raise ValueError(f"BCV: no se encontro la tasa '{key}' en la pagina")
        rates[key] = _to_float(html.unescape(match.group(1)))
    date_match = _DATE_RE.search(page)
    if not date_match:
        raise ValueError("BCV: no se encontro la fecha valor")
    return BcvRates(usd=rates["dolar"], eur=rates["euro"], fecha_valor=date.fromisoformat(date_match.group(1)), fuente="bcv.org.ve")


def fetch_bcv(timeout: int = REQUEST_TIMEOUT, max_retries: int = 2) -> BcvRates:
    last_error: Optional[Exception] = None
    for _ in range(max_retries):
        try:
            resp = requests.get(BCV_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, verify=_ca_bundle())
            resp.raise_for_status()
            return parse_bcv_html(resp.text)
        except (requests.RequestException, ValueError) as e:
            last_error = e
    raise RuntimeError(f"BCV: fallaron {max_retries} intentos: {last_error}") from last_error


def fetch_bcv_with_fallback(timeout: int = REQUEST_TIMEOUT, max_retries: int = 2) -> BcvRates:
    """bcv.org.ve primero; si falla, DolarAPI (que replica al BCV)."""
    try:
        return fetch_bcv(timeout=timeout, max_retries=max_retries)
    except RuntimeError as bcv_error:
        usd = dolarapi.fetch_usd_official(timeout=timeout, max_retries=max_retries)
        eur = dolarapi.fetch_eur_official(timeout=timeout, max_retries=max_retries)
        fecha = date.fromisoformat(usd.fecha_actualizacion[:10]) if usd.fecha_actualizacion else date.today()
        return BcvRates(usd=usd.promedio, eur=eur.promedio, fecha_valor=fecha, fuente=f"DolarAPI (BCV no disponible: {bcv_error})")
