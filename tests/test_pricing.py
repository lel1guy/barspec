"""The money: pure cost/ABV/pricing math. No DB involved."""
import pytest

import pricing


def line(name="X", ml=30.0, abv=40.0, price=22.0, vol=700.0):
    return {"name": name, "amount_ml": ml, "abv": abv,
            "bottle_price_eur": price, "bottle_volume_ml": vol}


class TestCost:
    def test_line_cost_per_ml(self):
        assert pricing.line_cost(line()) == pytest.approx(30 * 22.0 / 700, abs=1e-9)

    def test_drink_cost_sums_lines(self):
        lines = [line(ml=30, price=22), line(ml=30, price=19), line(ml=30, price=11, vol=750)]
        expected = 30 * 22 / 700 + 30 * 19 / 700 + 30 * 11 / 750
        assert pricing.drink_cost(lines) == pytest.approx(expected, abs=1e-9)

    def test_unpriced_bottle_costs_zero(self):
        # bottle_price 0 or volume 0 => no cost, never a crash
        assert pricing.line_cost(line(price=0.0)) == 0.0
        assert pricing.line_cost(line(vol=0.0)) == 0.0

    def test_volume_zero_guard(self):
        assert pricing.drink_abv([]) == 0.0
        assert pricing.summarize([])["cost_eur"] == 0.0


class TestABV:
    def test_volume_weighted(self):
        # 30 ml at 40% + 30 ml at 0% -> 20%
        lines = [line(ml=30, abv=40), line(ml=30, abv=0)]
        assert pricing.drink_abv(lines) == pytest.approx(20.0)

    def test_matches_aperol_spritz_reality(self):
        lines = [
            line("Aperol", 60, 11, 15.0, 700),
            line("Prosecco", 90, 11.5, 8.0, 750),
            line("Soda", 20, 0, 1.2, 1500),
        ]
        # (60*.11 + 90*.115 + 20*0) / 170 * 100
        assert pricing.drink_abv(lines) == pytest.approx((6.6 + 10.35) / 170 * 100)


class TestSuggestedPrice:
    def test_gp75_rounds_up_to_half(self):
        # cost 2.20 at 75% GP -> 8.80 raw -> ceil to 9.0
        assert pricing.suggested_price(2.20, 75) == 9.0

    def test_gp70(self):
        # 2.20 / 0.30 = 7.333 -> 7.5
        assert pricing.suggested_price(2.20, 70) == 7.5

    def test_never_dips_below_target(self):
        # ceil-to-.5 guarantees margin >= target after rounding
        for cost in (1.0, 1.33, 2.05, 3.71, 12.34):
            price = pricing.suggested_price(cost, 70)
            assert pricing.margin_pct(price, cost) >= 70.0 - 1e-9

    def test_zero_cost_zero_price(self):
        assert pricing.suggested_price(0.0, 70) == 0.0

    def test_menu_round(self):
        assert pricing.menu_round_up(7.333) == 7.5
        assert pricing.menu_round_up(8.8) == 9.0


class TestMargin:
    def test_margin_pct(self):
        assert pricing.margin_pct(9.0, 2.2) == pytest.approx((9 - 2.2) / 9 * 100)

    def test_unpriced(self):
        assert pricing.margin_pct(0.0, 2.2) == 0.0
        assert pricing.margin_band(0, 70) == "unpriced"

    def test_bands(self):
        assert pricing.margin_band(80, 70) == "good"
        assert pricing.margin_band(70, 70) == "good"
        assert pricing.margin_band(63, 70) == "ok"
        assert pricing.margin_band(40, 70) == "low"


class TestRowPcts:
    def test_sums_to_100(self):
        lines = [line(ml=30, price=22), line(ml=30, price=19), line(ml=60, price=15)]
        assert sum(pricing.row_pcts(lines)) == pytest.approx(100.0)

    def test_zero_cost_all_zero(self):
        assert pricing.row_pcts([line(price=0), line(price=0)]) == [0.0, 0.0]
