from __future__ import annotations

import pytest

from dca_bot.dca import DCAStrategy, average_cost_basis


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        DCAStrategy(quote_amount=0, interval=5)
    with pytest.raises(ValueError):
        DCAStrategy(quote_amount=-10, interval=5)
    with pytest.raises(ValueError):
        DCAStrategy(quote_amount=100, interval=0)
    with pytest.raises(ValueError):
        DCAStrategy(quote_amount=100, interval=-1)


def test_buys_only_on_interval() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=5)
    # 20 ticks -> buys at 0, 5, 10, 15 == 4 buys.
    prices = [10.0] * 20
    result = strat.run(prices)
    assert [b.tick for b in result.buys] == [0, 5, 10, 15]
    assert result.buys[0].tick == 0
    assert all(b.tick % 5 == 0 for b in result.buys)


def test_should_buy_logic() -> None:
    strat = DCAStrategy(quote_amount=50.0, interval=3)
    assert strat.should_buy(0) is True
    assert strat.should_buy(3) is True
    assert strat.should_buy(1) is False
    assert strat.should_buy(2) is False
    with pytest.raises(ValueError):
        strat.should_buy(-1)


def test_average_cost_equals_spent_over_units() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    prices = [10.0, 20.0, 50.0, 100.0]
    result = strat.run(prices)
    # 4 buys of $100 each.
    assert result.total_spent == pytest.approx(400.0)
    expected_units = 100 / 10 + 100 / 20 + 100 / 50 + 100 / 100
    assert result.total_units == pytest.approx(expected_units)
    assert result.average_cost == pytest.approx(result.total_spent / result.total_units)


def test_units_equal_quote_over_price() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    buy = strat.buy_at(tick=0, price=25.0)
    assert buy.units == pytest.approx(4.0)
    assert buy.quote_amount == pytest.approx(100.0)


def test_run_rejects_empty_and_bad_prices() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    with pytest.raises(ValueError):
        strat.run([])
    with pytest.raises(ValueError):
        strat.run([10.0, -5.0])


def test_average_cost_basis_requires_positive_units() -> None:
    assert average_cost_basis(400.0, 8.0) == pytest.approx(50.0)
    with pytest.raises(ValueError):
        average_cost_basis(400.0, 0.0)
