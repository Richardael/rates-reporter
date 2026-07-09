from typing import Tuple


def apply_adjustments(
    base_rate: float,
    percent_subtract: float = 0.0,
    fixed_subtract_bs: float = 0.0,
    round_decimals: int = 2,
) -> Tuple[float, str]:
    if base_rate <= 0:
        raise ValueError(f"La tasa base debe ser mayor a cero. Recibido: {base_rate}")

    has_percent = percent_subtract > 0
    has_fixed = fixed_subtract_bs > 0

    adjusted = base_rate

    if has_percent:
        adjusted *= (1.0 - percent_subtract / 100.0)

    if has_fixed:
        adjusted -= fixed_subtract_bs

    if adjusted <= 0:
        raise ValueError(
            f"La tasa ajustada resultó negativa o cero ({adjusted}). "
            f"Verifique los descuentos configurados."
        )

    adjusted = round(adjusted, round_decimals)

    if not has_percent and not has_fixed:
        rule = "Sin ajuste"
    else:
        parts = []
        if has_percent:
            parts.append(f"-{percent_subtract}%")
        if has_fixed:
            parts.append(f"-{fixed_subtract_bs:,.2f} Bs")
        rule = " y ".join(parts)

    return adjusted, rule
