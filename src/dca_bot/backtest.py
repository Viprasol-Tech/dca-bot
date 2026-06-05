"""Backtest a DCA strategy over a historical price series.

Replays a :class:`~dca_bot.dca.DCAStrategy` against a list of prices, feeding
each buy into a :class:`~dca_bot.portfolio.Portfolio`, and reports the units
accumulated, average cost, final mark-to-market value and ROI.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from dca_bot.dca import DCAStrategy
from dca_bot.portfolio import Portfolio


@dataclass(frozen=True)
class BacktestResult:
    """Outcome of a DCA backtest over a price series.

    Attributes:
        num_buys: Number of buys executed.
        total_units: Total units accumulated.
        total_spent: Total quote currency spent.
        average_cost: Average quote currency paid per unit.
        final_price: The last price in the series.
        final_value: Mark-to-market value at ``final_price``.
        pnl: Profit/loss, ``final_value - total_spent``.
        roi: Return on investment as a fraction of ``total_spent``.
    """

    num_buys: int
    total_units: float
    total_spent: float
    average_cost: float
    final_price: float
    final_value: float
    pnl: float
    roi: float


def run_backtest(strategy: DCAStrategy, prices: list[float]) -> BacktestResult:
    """Run ``strategy`` over ``prices`` and report the result.

    Args:
        strategy: The DCA strategy to replay.
        prices: Sequence of positive unit prices, one per tick.

    Returns:
        A :class:`BacktestResult` summarising the run.

    Raises:
        ValueError: If ``prices`` is empty or contains a non-positive price.
    """
    if not prices:
        raise ValueError("prices must not be empty")

    portfolio = Portfolio()
    result = strategy.run(prices)
    for buy in result.buys:
        portfolio.buy(buy.quote_amount, buy.price)

    final_price = prices[-1]
    final_value = portfolio.value(final_price)
    total_spent = portfolio.cost_basis
    pnl = final_value - total_spent
    roi = pnl / total_spent if total_spent > 0 else 0.0

    return BacktestResult(
        num_buys=len(result.buys),
        total_units=portfolio.units,
        total_spent=total_spent,
        average_cost=portfolio.average_price,
        final_price=final_price,
        final_value=final_value,
        pnl=pnl,
        roi=roi,
    )
