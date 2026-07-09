import statistics
from typing import List, Optional

import requests

from src.models import RateData


DOLARAPI_BASE = "https://ve.dolarapi.com/v1"
REQUEST_TIMEOUT = 15


def _do_get(url: str, timeout: int = REQUEST_TIMEOUT, max_retries: int = 2) -> dict:
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < max_retries:
                continue
    raise RuntimeError(f"DolarAPI: fallaron {max_retries} intentos") from last_error


def fetch_usd_official(timeout: int = REQUEST_TIMEOUT, max_retries: int = 2) -> RateData:
    data = _do_get(f"{DOLARAPI_BASE}/dolares/oficial", timeout=timeout, max_retries=max_retries)

    if isinstance(data, dict) and "promedio" in data:
        return RateData(
            promedio=float(data["promedio"]),
            fecha_actualizacion=str(data.get("fechaActualizacion", "")),
            fuente=str(data.get("fuente", "BCV")),
            nombre=str(data.get("nombre", "Oficial")),
        )

    raise ValueError(f"DolarAPI USD: respuesta inesperada: {data}")


def fetch_eur_official(timeout: int = REQUEST_TIMEOUT, max_retries: int = 2) -> RateData:
    data = _do_get(f"{DOLARAPI_BASE}/euros", timeout=timeout, max_retries=max_retries)

    if isinstance(data, list):
        for entry in data:
            fuente = str(entry.get("fuente", "")).lower()
            nombre = str(entry.get("nombre", "")).lower()
            if "bcv" in fuente or "bcv" in nombre or "oficial" in nombre:
                return RateData(
                    promedio=float(entry["promedio"]),
                    fecha_actualizacion=str(entry.get("fechaActualizacion", "")),
                    fuente=str(entry.get("fuente", "")),
                    nombre=str(entry.get("nombre", "")),
                )
        if data:
            entry = data[0]
            return RateData(
                promedio=float(entry["promedio"]),
                fecha_actualizacion=str(entry.get("fechaActualizacion", "")),
                fuente=str(entry.get("fuente", "")),
                nombre=str(entry.get("nombre", "")),
            )
        raise ValueError("DolarAPI EUR: lista vacia")

    if isinstance(data, dict) and "promedio" in data:
        return RateData(
            promedio=float(data["promedio"]),
            fecha_actualizacion=str(data.get("fechaActualizacion", "")),
            fuente=str(data.get("fuente", "BCV")),
            nombre=str(data.get("nombre", "Oficial")),
        )

    raise ValueError(f"DolarAPI EUR: respuesta inesperada: {data}")
