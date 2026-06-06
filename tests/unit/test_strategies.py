from __future__ import annotations

import pytest

from dca_bot.dca import DCAStrategy
from dca_bot.strategies import (
    DipBuyStrategy,
    Strategy,
    ValueAveragingStrategy,
    build_strategy,
)


def test_value_averaging_hits_target_value() -> None:
    # value_step=100, interval=1, flat price 10 -> target grows 100, 200, 300...
    strat = ValueAveragingStrategy(value_step=100.0, interval=1)
    prices = [10.0, 10.0, 10.0]
    result = strat.run(prices)
    # At flat price each tick buys exactly $100 worth.
    assert result.total_spent == pytest.approx(300.0)
    assert result.total_units == pytest.approx(30.0)
    assert [b.quote_amount for b in result.buys] == pytest.approx([100.0, 100.0, 100.0])


def test_value_averaging_buys_more_on_dip_less_on_spike() -> None:
    strat = ValueAveragingStrategy(value_step=100.0, interval=1)
    # tick0: price 10 -> target 100, buy $100 -> 10 units, value 100
    # tick1: price 5  -> target 200, value 50, gap 150 -> buy $150
    # tick2: price 20 -> target 300, value now (10+30)=40 units *20=800 > 300 -> no buy
    result = strat.run([10.0, 5.0, 20.0])
    spends = [b.quote_amount for b in result.buys]
    assert spends[0] == pytest.approx(100.0)
    assert spends[1] == pytest.approx(150.0)
    # Spike tick produced no buy (never sells).
    assert len(result.buys) == 2


def test_value_averaging_respects_max_buy_cap() -> None:
    strat = ValueAveragingStrategy(value_step=100.0, interval=1, max_buy=120.0)
    # tick0 price 10 -> gap 100 (under cap). tick1 price 5 -> gap 150 capped to 120.
    result = strat.run([10.0, 5.0])
    assert result.buys[1].quote_amount == pytest.approx(120.0)


def test_value_averaging_validation() -> None:
    with pytest.raises(ValueError):
        ValueAveragingStrategy(value_step=0)
    with pytest.raises(ValueError):
        ValueAveragingStrategy(value_step=100, interval=0)
    with pytest.raises(ValueError):
        ValueAveragingStrategy(value_step=100, max_buy=0)
    with pytest.raises(ValueError):
        ValueAveragingStrategy(value_step=100).run([])
    with pytest.raises(ValueError):
        ValueAveragingStrategy(value_step=100).run([10.0, -1.0])


def test_dip_buy_equals_dca_when_multiplier_zero() -> None:
    dip = DipBuyStrategy(base_amount=100.0, interval=1, dip_multiplier=0.0)
    dca = DCAStrategy(quote_amount=100.0, interval=1)
    prices = [10.0, 8.0, 12.0, 6.0]
    dip_result = dip.run(prices)
    dca_result = dca.run(prices)
    assert dip_result.total_spent == pytest.approx(dca_result.total_spent)
    assert dip_result.total_units == pytest.approx(dca_result.total_units)


def test_dip_buy_spends_more_in_drawdown() -> None:
    dip = DipBuyStrategy(base_amount=100.0, interval=1, dip_multiplier=2.0)
    # high=100, price drops to 50 -> drawdown 0.5 -> scale 1+2*0.5=2 -> spend 200.
    result = dip.run([100.0, 50.0])
    assert result.buys[0].quote_amount == pytest.approx(100.0)
    assert result.buys[1].quote_amount == pytest.approx(200.0)


def test_dip_buy_caps_at_max_multiple() -> None:
    dip = DipBuyStrategy(base_amount=100.0, dip_multiplier=10.0, max_multiple=3.0)
    # drawdown 0.9 -> raw scale 1+10*0.9=10 capped to 3 -> spend 300.
    spend = dip.spend_for(price=10.0, running_high=100.0)
    assert spend == pytest.approx(300.0)


def test_dip_buy_validation() -> None:
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=0)
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=100, interval=0)
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=100, dip_multiplier=-1)
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=100, max_multiple=0.5)
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=100).spend_for(price=0, running_high=100)
    with pytest.raises(ValueError):
        DipBuyStrategy(base_amount=100).spend_for(price=10, running_high=0)


def test_build_strategy_dispatch_and_aliases() -> None:
    assert isinstance(build_strategy("dca", amount=100), DCAStrategy)
    assert isinstance(build_strategy("value", amount=100), ValueAveragingStrategy)
    assert isinstance(build_strategy("VA", amount=100), ValueAveragingStrategy)
    assert isinstance(build_strategy("dip", amount=100), DipBuyStrategy)
    with pytest.raises(ValueError):
        build_strategy("nope", amount=100)


def test_strategies_satisfy_protocol() -> None:
    for strat in (
        DCAStrategy(quote_amount=100, interval=1),
        ValueAveragingStrategy(value_step=100),
        DipBuyStrategy(base_amount=100),
    ):
        assert isinstance(strat, Strategy)
