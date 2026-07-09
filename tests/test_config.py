import os
import tempfile

import pytest

from src.config import AppConfig, RateConfig, load_config


class TestLoadConfig:
    def test_load_valid_yaml(self):
        yaml_content = """
timezone: "America/Caracas"
round_decimals: 3
output:
  print_console: true
  save_to_file: false
  output_file: "test-output.txt"
callmebot:
  enabled: true
  recipients:
    - phone: "584141234567"
      apikey: "key_abc"
      name: "Test Person"
    - phone: "584128027107"
      apikey: "key_xyz"
rates:
  bcv_usd:
    enabled: true
    label: "USD"
    provider: "dolarapi_usd_official"
    adjustments:
      percent_subtract: 0.0
      fixed_subtract_bs: 0.0
  bcv_eur:
    enabled: false
    label: "EUR"
    provider: "dolarapi_eur_official"
    adjustments:
      percent_subtract: 1.0
      fixed_subtract_bs: 5.0
  binance_usdt:
    enabled: true
    label: "USDT"
    provider: "binance_p2p"
    fallback_manual_rate: 790.0
    binance:
      asset: "USDT"
      fiat: "VES"
      trade_type: "BUY"
      rows: 5
      pay_types: ["BANK"]
      aggregation: "mean"
      merchant_check: true
    adjustments:
      percent_subtract: 0.2
      fixed_subtract_bs: 10.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = load_config(config_path)

            assert config.timezone == "America/Caracas"
            assert config.round_decimals == 3
            assert config.output.print_console is True
            assert config.output.save_to_file is False
            assert config.output.output_file == "test-output.txt"
            assert config.callmebot.enabled is True
            assert len(config.callmebot.recipients) == 2
            assert config.callmebot.recipients[0].phone == "584141234567"
            assert config.callmebot.recipients[0].apikey == "key_abc"
            assert config.callmebot.recipients[0].name == "Test Person"
            assert config.callmebot.recipients[0].label == "Test Person (584141234567)"
            assert config.callmebot.recipients[1].phone == "584128027107"
            assert config.callmebot.recipients[1].apikey == "key_xyz"
            assert config.callmebot.recipients[1].name == ""
            assert config.callmebot.recipients[1].label == "584128027107"

            bcv = config.get_rate_config("bcv_usd")
            assert bcv is not None
            assert bcv.enabled is True
            assert bcv.adjustments.percent_subtract == 0.0

            eur = config.get_rate_config("bcv_eur")
            assert eur is not None
            assert eur.enabled is False
            assert eur.adjustments.percent_subtract == 1.0
            assert eur.adjustments.fixed_subtract_bs == 5.0

            usdt = config.get_rate_config("binance_usdt")
            assert usdt is not None
            assert usdt.enabled is True
            assert usdt.fallback_manual_rate == 790.0
            assert usdt.binance is not None
            assert usdt.binance.trade_type == "BUY"
            assert usdt.binance.aggregation == "mean"
            assert usdt.binance.rows == 5
            assert usdt.binance.merchant_check is True
            assert usdt.adjustments.percent_subtract == 0.2

        finally:
            os.unlink(config_path)
