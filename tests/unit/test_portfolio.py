from __future__ import annotations

import pytest

from dca_bot.portfolio import MultiAssetPortfolio, Portfolio


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


def test_multi_asset_tracks_symbols_independently() -> None:
    mp = MultiAssetPortfolio()
    mp.buy("btc", 100.0, 10.0)  # 10 units of BTC
    mp.buy("ETH", 100.0, 50.0)  # 2 units of ETH
    assert mp.symbols == ["BTC", "ETH"]
    assert mp.holding("BTC").units == pytest.approx(10.0)
    assert mp.holding("eth").units == pytest.approx(2.0)
    assert mp.cost_basis() == pytest.approx(200.0)


def test_multi_asset_value_and_pnl() -> None:
    mp = MultiAssetPortfolio()
    mp.buy("BTC", 100.0, 10.0)  # 10 units
    mp.buy("ETH", 100.0, 50.0)  # 2 units
    prices = {"BTC": 20.0, "ETH": 50.0}
    # BTC: 10 * 20 = 200, ETH: 2 * 50 = 100 -> 300
    assert mp.value(prices) == pytest.approx(300.0)
    assert mp.unrealized_pnl(prices) == pytest.approx(100.0)


def test_multi_asset_weights_sum_to_one() -> None:
    mp = MultiAssetPortfolio()
    mp.buy("BTC", 100.0, 10.0)  # value 200 at price 20
    mp.buy("ETH", 100.0, 50.0)  # value 100 at price 50
    weights = mp.weights({"BTC": 20.0, "ETH": 50.0})
    assert weights["BTC"] == pytest.approx(200.0 / 300.0)
    assert weights["ETH"] == pytest.approx(100.0 / 300.0)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_multi_asset_missing_price_raises() -> None:
    mp = MultiAssetPortfolio()
    mp.buy("BTC", 100.0, 10.0)
    with pytest.raises(KeyError):
        mp.value({"ETH": 10.0})


def test_multi_asset_empty_symbol_and_pre_create() -> None:
    mp = MultiAssetPortfolio(symbols=["btc", "eth"])
    assert mp.symbols == ["BTC", "ETH"]
    assert mp.value({}) == pytest.approx(0.0)
    assert mp.weights({}) == {}
    with pytest.raises(ValueError):
        mp.buy("  ", 100.0, 10.0)
