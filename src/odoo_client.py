from typing import Any, Optional

import requests


class OdooClient:
    """Cliente minimo para la API JSON-2 de Odoo 19 (/json/2/<modelo>/<metodo>)."""

    def __init__(self, base_url: str, database: str, api_key: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.database = database
        self.api_key = api_key
        self.timeout = timeout

    def call(self, model: str, method: str, **params: Any) -> Any:
        resp = requests.post(
            f"{self.base_url}/json/2/{model}/{method}",
            json=params,
            headers={
                "Authorization": f"bearer {self.api_key}",
                "X-Odoo-Database": self.database,
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            try:
                message = resp.json().get("message", resp.text[:300])
            except ValueError:
                message = resp.text[:300]
            raise RuntimeError(f"Odoo {model}.{method}: HTTP {resp.status_code}: {message}")
        return resp.json()

    def search_read(self, model: str, domain: list, fields: list, context: Optional[dict] = None, **extra: Any) -> list:
        return self.call(model, "search_read", domain=domain, fields=fields, context=context or {}, **extra)

    def create(self, model: str, vals: dict, context: Optional[dict] = None) -> int:
        ids = self.call(model, "create", vals_list=[vals], context=context or {})
        return int(ids[0])

    def write(self, model: str, ids: list, vals: dict, context: Optional[dict] = None) -> None:
        self.call(model, "write", ids=ids, vals=vals, context=context or {})
