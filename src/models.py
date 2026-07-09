from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateResult:
    label: str
    provider_name: str
    base_rate: float
    adjusted_rate: float
    rule_description: str
    source: str
    updated_at: str
    available: bool = True
    error_message: Optional[str] = None


@dataclass
class RateData:
    promedio: float
    fecha_actualizacion: str
    fuente: str
    nombre: str
