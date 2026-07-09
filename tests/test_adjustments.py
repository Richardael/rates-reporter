import pytest

from src.adjustments import apply_adjustments


class TestApplyAdjustments:
    def test_percent_only(self):
        rate, rule = apply_adjustments(base_rate=780.0, percent_subtract=0.2, fixed_subtract_bs=0.0)
        assert rate == 778.44
        assert rule == "-0.2%"

    def test_fixed_only(self):
        rate, rule = apply_adjustments(base_rate=780.0, percent_subtract=0.0, fixed_subtract_bs=10.0)
        assert rate == 770.00
        assert rule == "-10.00 Bs"

    def test_combined(self):
        rate, rule = apply_adjustments(base_rate=780.0, percent_subtract=0.2, fixed_subtract_bs=10.0)
        assert rate == 768.44
        assert rule == "-0.2% y -10.00 Bs"

    def test_no_adjustments(self):
        rate, rule = apply_adjustments(base_rate=674.93, percent_subtract=0.0, fixed_subtract_bs=0.0)
        assert rate == 674.93
        assert rule == "Sin ajuste"

    def test_negative_or_zero_adjusted_raises(self):
        with pytest.raises(ValueError):
            apply_adjustments(base_rate=5.0, percent_subtract=0.0, fixed_subtract_bs=100.0)

    def test_zero_base_raises(self):
        with pytest.raises(ValueError):
            apply_adjustments(base_rate=0.0, percent_subtract=10.0, fixed_subtract_bs=0.0)

    def test_negative_base_raises(self):
        with pytest.raises(ValueError):
            apply_adjustments(base_rate=-1.0, percent_subtract=0.0, fixed_subtract_bs=0.0)

    def test_rounding_applied_at_end(self):
        rate, _ = apply_adjustments(base_rate=100.0, percent_subtract=0.15, fixed_subtract_bs=0.0)
        assert rate == 99.85

    def test_custom_round_decimals(self):
        rate, _ = apply_adjustments(
            base_rate=100.0, percent_subtract=0.12345, fixed_subtract_bs=0.0, round_decimals=4
        )
        assert rate == 99.8765
