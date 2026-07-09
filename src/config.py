import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class OutputConfig:
    print_console: bool = True
    save_to_file: bool = True
    output_file: str = "latest-rates-message.txt"


@dataclass
class CallMeBotRecipient:
    phone: str = ""
    apikey: str = ""
    name: str = ""

    def get_apikey(self) -> Optional[str]:
        return self.apikey or None

    @property
    def label(self) -> str:
        if self.name:
            return f"{self.name} ({self.phone})"
        return self.phone


@dataclass
class CallMeBotConfig:
    enabled: bool = False
    recipients: list = field(default_factory=list)

    def get_recipients(self) -> list:
        return [r for r in self.recipients if r.phone]


@dataclass
class AdjustmentsConfig:
    percent_subtract: float = 0.0
    fixed_subtract_bs: float = 0.0


@dataclass
class BinanceConfig:
    asset: str = "USDT"
    fiat: str = "VES"
    trade_type: str = "SELL"
    rows: int = 10
    pay_types: list = field(default_factory=list)
    aggregation: str = "median"
    merchant_check: bool = False


@dataclass
class RateConfig:
    enabled: bool = True
    label: str = ""
    provider: str = ""
    fallback_manual_rate: Optional[float] = None
    binance: Optional[BinanceConfig] = None
    adjustments: AdjustmentsConfig = field(default_factory=AdjustmentsConfig)


@dataclass
class AppConfig:
    timezone: str = "America/Caracas"
    round_decimals: int = 2
    output: OutputConfig = field(default_factory=OutputConfig)
    callmebot: CallMeBotConfig = field(default_factory=CallMeBotConfig)
    rates: dict = field(default_factory=dict)
    request_timeout: int = 15
    max_retries: int = 2
    retry_backoff: float = 1.0

    def get_rate_config(self, key: str) -> Optional[RateConfig]:
        raw = self.rates.get(key)
        if raw is None:
            return None
        if isinstance(raw, RateConfig):
            return raw

        adj_raw = raw.get("adjustments", {})
        adjustments = AdjustmentsConfig(
            percent_subtract=float(adj_raw.get("percent_subtract", 0.0)),
            fixed_subtract_bs=float(adj_raw.get("fixed_subtract_bs", 0.0)),
        )

        binance = None
        bin_raw = raw.get("binance")
        if bin_raw:
            binance = BinanceConfig(
                asset=bin_raw.get("asset", "USDT"),
                fiat=bin_raw.get("fiat", "VES"),
                trade_type=bin_raw.get("trade_type", "SELL"),
                rows=int(bin_raw.get("rows", 10)),
                pay_types=bin_raw.get("pay_types", []),
                aggregation=bin_raw.get("aggregation", "median"),
                merchant_check=bool(bin_raw.get("merchant_check", False)),
            )

        return RateConfig(
            enabled=bool(raw.get("enabled", True)),
            label=str(raw.get("label", "")),
            provider=str(raw.get("provider", "")),
            fallback_manual_rate=raw.get("fallback_manual_rate"),
            binance=binance,
            adjustments=adjustments,
        )


def load_config(config_path: str) -> AppConfig:
    load_dotenv()

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    output_raw = raw.get("output", {})
    output = OutputConfig(
        print_console=bool(output_raw.get("print_console", True)),
        save_to_file=bool(output_raw.get("save_to_file", True)),
        output_file=str(output_raw.get("output_file", "latest-rates-message.txt")),
    )

    callmebot_raw = raw.get("callmebot", {})
    recipients = []
    for r_raw in callmebot_raw.get("recipients", []):
        if isinstance(r_raw, dict):
            phone = str(r_raw.get("phone", ""))
            phone_env = r_raw.get("phone_env", "")
            if phone_env:
                phone = os.getenv(phone_env, phone)
            apikey = str(r_raw.get("apikey", ""))
            apikey_env = r_raw.get("apikey_env", "")
            if apikey_env:
                apikey = os.getenv(apikey_env, apikey)
            recipients.append(CallMeBotRecipient(phone=phone, apikey=apikey, name=str(r_raw.get("name", ""))))
        elif isinstance(r_raw, str) and r_raw:
            recipients.append(CallMeBotRecipient(phone=r_raw))

    callmebot = CallMeBotConfig(
        enabled=bool(callmebot_raw.get("enabled", False)),
        recipients=recipients,
    )

    rates_raw = raw.get("rates", {})

    return AppConfig(
        timezone=str(raw.get("timezone", "America/Caracas")),
        round_decimals=int(raw.get("round_decimals", 2)),
        output=output,
        callmebot=callmebot,
        rates=rates_raw,
    )
