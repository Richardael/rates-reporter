from datetime import date

import pytest

import odoo_sync
from odoo_sync import company_rates, rate_plan
from src.providers.bcv import BcvRates, parse_bcv_html


BCV_SNIPPET = """
<div id="euro" class="col-sm-12 col-xs-12 "><div class="field-content"><div class="row recuadrotsmc">
<div class="col-sm-6 col-xs-6"><img src="/euro.png"/> <span> EUR </span></div>
<div class="col-sm-6 col-xs-6 centrado"><strong> 992,80018713 </strong> </div></div></div></div>
<div id="dolar" class="col-sm-12 col-xs-12 "><div class="field-content"><div class="row recuadrotsmc">
<div class="col-sm-6 col-xs-6"><img src="/usd.png"/> <span> USD </span></div>
<div class="col-sm-6 col-xs-6 centrado textp"> <strong class="strong-tb">889,25530000</strong>  </div></div></div></div>
<div class="pull-right dinpro center">Fecha Valor: <span class="date-display-single" property="dc:date"
 datatype="xsd:dateTime" content="2026-10-30T00:00:00-04:00">Viernes, 30 Octubre  2026</span></div>
"""


class TestParseBcv:
    def test_rates_and_date(self):
        rates = parse_bcv_html(BCV_SNIPPET)
        assert rates.usd == 889.2553
        assert rates.eur == 992.80018713
        assert rates.fecha_valor == date(2026, 10, 30)

    def test_thousands_separator(self):
        rates = parse_bcv_html(BCV_SNIPPET.replace("889,25530000", "1.889,25530000"))
        assert rates.usd == 1889.2553

    def test_missing_rate(self):
        with pytest.raises(ValueError):
            parse_bcv_html(BCV_SNIPPET.replace('id="dolar"', 'id="otro"'))


class TestCompanyRates:
    bs_per = {"VEF": 1.0, "USD": 889.2553, "EUR": 992.80018713}

    def test_usd_company(self):
        rates = company_rates(self.bs_per, "USD")
        assert rates["VEF"] == pytest.approx(889.2553)
        assert rates["EUR"] == pytest.approx(889.2553 / 992.80018713)
        assert "USD" not in rates

    def test_vef_company(self):
        rates = company_rates(self.bs_per, "VEF")
        assert rates["USD"] == pytest.approx(1 / 889.2553)
        assert rates["EUR"] == pytest.approx(1 / 992.80018713)


class TestRatePlan:
    bcv = BcvRates(usd=889.5754, eur=1000.0, fecha_valor=date(2026, 11, 3), fuente="bcv.org.ve")
    today = date(2026, 11, 2)

    @pytest.fixture(autouse=True)
    def binance_companies(self, monkeypatch):
        monkeypatch.setattr(odoo_sync, "BINANCE_RATE_COMPANY_IDS", {32, 33})

    def test_bcv_company_uses_value_date(self):
        day, bs_per = rate_plan(30, self.bcv, 995.35, self.today)
        assert day == "2026-11-03"
        assert bs_per["USD"] == 889.5754

    def test_binance_company_uses_today_and_buy_rate(self):
        day, bs_per = rate_plan(33, self.bcv, 995.35, self.today)
        assert day == "2026-11-02"
        rates = company_rates(bs_per, "USD")
        assert rates["VEF"] == pytest.approx(995.35)
        assert rates["EUR"] == pytest.approx(889.5754 / 1000.0)  # EUR/USD del BCV

    def test_binance_company_without_bcv_still_gets_vef(self):
        _, bs_per = rate_plan(32, None, 995.35, self.today)
        assert company_rates(bs_per, "USD") == {"VEF": pytest.approx(995.35)}

    def test_missing_source_returns_none(self):
        assert rate_plan(33, self.bcv, None, self.today) is None
        assert rate_plan(30, None, 995.35, self.today) is None
