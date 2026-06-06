from __future__ import annotations

import pytest

from dca_bot.config import AssetConfig, BotConfig
from dca_bot.dca import DCAStrategy
from dca_bot.report import (
    AssetReport,
    PortfolioReport,
    report_portfolio,
    report_strategy,
)


def test_report_strategy_cost_advantage_positive_when_avg_below_market() -> None:
    # Prices rise: average cost ends below final market price -> positive advantage.
    strat = DCAStrategy(quote_amount=100.0, interval=1)
    report = report_strategy("BTC", strat, [10.0, 20.0])
    assert report.symbol == "BTC"
    assert report.market_price == pytest.approx(20.0)
    assert report.average_cost < report.market_price
    assert report.cost_advantage > 0
    assert report.roi > 0


def test_report_strategy_drawdown_recorded() -> None:
    # Single buy at tick 0 (interval > series length), then the price crashes so
    # the equity curve falls without any later buy masking the drawdown.
    strat = DCAStrategy(quote_amount=100.0, interval=10)
    report = report_strategy("ETH", strat, [100.0, 50.0])
    assert report.max_drawdown == pytest.approx(0.5)


def test_portfolio_report_aggregates() -> None:
    a = AssetReport(
        symbol="BTC",
        strategy="dca",
        total_spent=100.0,
        total_units=1.0,
        average_cost=100.0,
        market_price=150.0,
        final_value=150.0,
        roi=0.5,
        max_drawdown=0.1,
        cost_advantage=0.3333,
    )
    b = AssetReport(
        symbol="ETH",
        strategy="dip-buy",
        total_spent=100.0,
        total_units=2.0,
        average_cost=50.0,
        market_price=40.0,
        final_value=80.0,
        roi=-0.2,
        max_drawdown=0.3,
        cost_advantage=-0.25,
    )
    roll = PortfolioReport.from_assets([a, b])
    assert roll.total_spent == pytest.approx(200.0)
    assert roll.total_value == pytest.approx(230.0)
    assert roll.roi == pytest.approx(0.15)
    assert roll.worst_drawdown == pytest.approx(0.3)


def test_portfolio_report_rejects_empty() -> None:
    with pytest.raises(ValueError):
        PortfolioReport.from_assets([])


def test_report_portfolio_end_to_end() -> None:
    cfg = BotConfig(
        assets=[
            AssetConfig(symbol="BTC", strategy="dca", amount=100, interval=1),
            AssetConfig(symbol="ETH", strategy="dip-buy", amount=50, interval=1),
        ]
    )
    series = {"BTC": [10.0, 20.0], "ETH": [10.0, 5.0]}
    roll = report_portfolio(cfg, series)
    assert {a.symbol for a in roll.assets} == {"BTC", "ETH"}
    assert roll.total_spent > 0


def test_report_portfolio_missing_series_raises() -> None:
    cfg = BotConfig(assets=[AssetConfig(symbol="BTC", amount=100)])
    with pytest.raises(KeyError):
        report_portfolio(cfg, {"ETH": [10.0, 20.0]})
