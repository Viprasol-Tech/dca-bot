from __future__ import annotations

import pytest

from dca_bot.portfolio import Portfolio


def test_empty_portfolio_average_price_is_zero() -> None:
    p = Portfolio()
    assert p.units == 0.0
    assert p.cost_basis == 0.0
    assert p.average_price == 0.0


def test_buy_accumulates_units_and_cost_basis() -> None:
    p = Portfolio()
    units = p.buy(quote_amount=100.0, price=20.0)
    assert units == pytest.approx(5.0)
    assert p.units == pytest.approx(5.0)
    assert p.cost_basis == pytest.approx(100.0)


def test_average_price_equals_cost_over_units() -> None:
    p = Portfolio()
    p.buy(100.0, 10.0)  # 10 units
    p.buy(100.0, 50.0)  # 2 units
    assert p.units == pytest.approx(12.0)
    assert p.cost_basis == pytest.approx(200.0)
    assert p.average_price == pytest.approx(200.0 / 12.0)


def test_value_and_unrealized_pnl() -> None:
    p = Portfolio()
    p.buy(100.0, 10.0)  # 10 units, cost 100
    assert p.value(20.0) == pytest.approx(200.0)
    assert p.unrealized_pnl(20.0) == pytest.approx(100.0)
    assert p.unrealized_pnl(5.0) == pytest.approx(-50.0)


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        Portfolio(units=-1)
    with pytest.raises(ValueError):
        Portfolio(cost_basis=-1)
    p = Portfolio()
    with pytest.raises(ValueError):
        p.buy(0.0, 10.0)
    with pytest.raises(ValueError):
        p.buy(100.0, 0.0)
    with pytest.raises(ValueError):
        p.value(-1.0)
