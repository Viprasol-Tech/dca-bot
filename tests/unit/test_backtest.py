from __future__ import annotations

import pytest

from dca_bot.backtest import run_backtest
from dca_bot.dca import DCAStrategy


def test_backtest_basic_accumulation() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    prices = [10.0, 20.0, 50.0, 100.0]
    result = run_backtest(strat, prices)
    assert result.num_buys == 4
    assert result.total_spent == pytest.approx(400.0)
    expected_units = 100 / 10 + 100 / 20 + 100 / 50 + 100 / 100
    assert result.total_units == pytest.approx(expected_units)
    assert result.average_cost == pytest.approx(400.0 / expected_units)


def test_backtest_final_value_and_pnl() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    prices = [10.0, 10.0]  # 20 units total, cost 200, final price 10
    result = run_backtest(strat, prices)
    assert result.total_units == pytest.approx(20.0)
    assert result.final_price == pytest.approx(10.0)
    assert result.final_value == pytest.approx(200.0)
    assert result.pnl == pytest.approx(0.0)
    assert result.roi == pytest.approx(0.0)


def test_backtest_profit_when_price_rises() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    prices = [10.0, 20.0]  # buys: 10u@10 + 5u@20 = 15u, cost 200, final 20 -> 300
    result = run_backtest(strat, prices)
    assert result.final_value == pytest.approx(300.0)
    assert result.pnl == pytest.approx(100.0)
    assert result.roi == pytest.approx(0.5)


def test_backtest_rejects_empty() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    with pytest.raises(ValueError):
        run_backtest(strat, [])


def test_backtest_reports_strategy_name() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    result = run_backtest(strat, [10.0, 12.0])
    assert result.strategy == "dca"


def test_backtest_no_drawdown_when_monotonic_rise() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    result = run_backtest(strat, [10.0, 20.0, 30.0])
    assert result.max_drawdown == pytest.approx(0.0)


def test_backtest_drawdown_on_crash() -> None:
    strat = DCAStrategy(quote_amount=100.0, interval=10)  # single buy at tick 0
    # Buy 10 units @ 100 (value 1000). Price falls to 50 -> value 500 -> dd 0.5.
    prices = [100.0] + [50.0] * 9
    result = run_backtest(strat, prices)
    assert result.num_buys == 1
    assert result.max_drawdown == pytest.approx(0.5)


def test_backtest_runs_value_averaging_and_dip() -> None:
    from dca_bot.strategies import DipBuyStrategy, ValueAveragingStrategy

    prices = [100.0, 80.0, 120.0, 90.0]
    va = run_backtest(ValueAveragingStrategy(value_step=100.0, interval=1), prices)
    dip = run_backtest(DipBuyStrategy(base_amount=100.0, interval=1), prices)
    assert va.strategy == "value-averaging"
    assert dip.strategy == "dip-buy"
    assert va.total_spent > 0
    assert dip.total_spent > 0
