"""Performance reporting for accumulation backtests.

Turns one or more :class:`~dca_bot.backtest.BacktestResult` runs into rich,
comparable metrics: average cost versus the final market price, ROI, max
drawdown, and the cost-basis advantage (how much cheaper the average entry was
than buying everything at the final price). A :class:`PortfolioReport` rolls
several per-asset runs into one capital-weighted summary.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from dca_bot.backtest import BacktestResult, run_backtest
from dca_bot.config import BotConfig
from dca_bot.strategies import Strategy


@dataclass(frozen=True)
class AssetReport:
    """Per-asset performance summary derived from a backtest.

    Attributes:
        symbol: Asset symbol.
        strategy: Strategy name that produced the run.
        total_spent: Quote currency invested.
        total_units: Units accumulated.
        average_cost: Average quote currency paid per unit.
        market_price: Final market price the position is marked at.
        final_value: Mark-to-market value at ``market_price``.
        roi: Return on investment as a fraction of ``total_spent``.
        max_drawdown: Worst peak-to-trough decline of the equity curve.
        cost_advantage: Fraction by which ``average_cost`` undercuts
            ``market_price``; positive means the average entry was cheaper.
    """

    symbol: str
    strategy: str
    total_spent: float
    total_units: float
    average_cost: float
    market_price: float
    final_value: float
    roi: float
    max_drawdown: float
    cost_advantage: float

    @classmethod
    def from_backtest(cls, symbol: str, result: BacktestResult) -> AssetReport:
        """Build an :class:`AssetReport` from a :class:`BacktestResult`."""
        if result.final_price > 0:
            advantage = (result.final_price - result.average_cost) / result.final_price
        else:
            advantage = 0.0
        return cls(
            symbol=symbol.strip().upper(),
            strategy=result.strategy,
            total_spent=result.total_spent,
            total_units=result.total_units,
            average_cost=result.average_cost,
            market_price=result.final_price,
            final_value=result.final_value,
            roi=result.roi,
            max_drawdown=result.max_drawdown,
            cost_advantage=advantage,
        )


@dataclass(frozen=True)
class PortfolioReport:
    """Capital-weighted roll-up of several :class:`AssetReport` entries.

    Attributes:
        assets: The per-asset reports.
        total_spent: Total quote currency invested across all assets.
        total_value: Total mark-to-market value across all assets.
        roi: Aggregate ROI as a fraction of ``total_spent``.
        worst_drawdown: The largest per-asset max drawdown.
    """

    assets: list[AssetReport]
    total_spent: float
    total_value: float
    roi: float
    worst_drawdown: float

    @classmethod
    def from_assets(cls, assets: list[AssetReport]) -> PortfolioReport:
        """Aggregate per-asset reports into one portfolio summary.

        Args:
            assets: Non-empty list of per-asset reports.

        Returns:
            The aggregated :class:`PortfolioReport`.

        Raises:
            ValueError: If ``assets`` is empty.
        """
        if not assets:
            raise ValueError("assets must not be empty")
        total_spent = sum(a.total_spent for a in assets)
        total_value = sum(a.final_value for a in assets)
        roi = (total_value - total_spent) / total_spent if total_spent > 0 else 0.0
        worst_drawdown = max(a.max_drawdown for a in assets)
        return cls(
            assets=assets,
            total_spent=total_spent,
            total_value=total_value,
            roi=roi,
            worst_drawdown=worst_drawdown,
        )


def report_strategy(symbol: str, strategy: Strategy, prices: list[float]) -> AssetReport:
    """Backtest ``strategy`` on ``prices`` and produce an :class:`AssetReport`.

    Args:
        symbol: Asset symbol for labelling.
        strategy: Strategy to backtest.
        prices: Positive price series.

    Returns:
        The per-asset performance report.
    """
    result = run_backtest(strategy, prices)
    return AssetReport.from_backtest(symbol, result)


def report_portfolio(config: BotConfig, price_series: dict[str, list[float]]) -> PortfolioReport:
    """Backtest every asset in ``config`` and roll the results up.

    Args:
        config: The bot configuration describing each asset's strategy.
        price_series: Mapping of symbol to its price series. Every configured
            symbol must be present.

    Returns:
        The aggregated :class:`PortfolioReport`.

    Raises:
        KeyError: If a configured symbol has no price series.
    """
    available = {s.strip().upper(): v for s, v in price_series.items()}
    reports: list[AssetReport] = []
    for asset in config.assets:
        if asset.symbol not in available:
            raise KeyError(f"missing price series for {asset.symbol}")
        reports.append(report_strategy(asset.symbol, asset.build(), available[asset.symbol]))
    return PortfolioReport.from_assets(reports)
