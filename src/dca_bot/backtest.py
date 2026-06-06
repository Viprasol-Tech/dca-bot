"""Backtest an accumulation strategy over a historical price series.

Replays any strategy implementing the :class:`~dca_bot.strategies.Strategy`
protocol (plain DCA, value averaging, dip-buy) against a list of prices, feeding
each buy into a :class:`~dca_bot.portfolio.Portfolio`, and reports the units
accumulated, average cost, final mark-to-market value, ROI and the worst
peak-to-trough drawdown of the position's equity curve.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from dca_bot.portfolio import Portfolio
from dca_bot.strategies import Strategy


@dataclass(frozen=True)
class BacktestResult:
    """Outcome of a strategy backtest over a price series.

    Attributes:
        strategy: Human-readable name of the strategy that was run.
        num_buys: Number of buys executed.
        total_units: Total units accumulated.
        total_spent: Total quote currency spent.
        average_cost: Average quote currency paid per unit.
        final_price: The last price in the series.
        final_value: Mark-to-market value at ``final_price``.
        pnl: Profit/loss, ``final_value - total_spent``.
        roi: Return on investment as a fraction of ``total_spent``.
        max_drawdown: Worst peak-to-trough decline of unrealised PnL across the
            series, as a non-negative fraction of the peak invested capital.
    """

    strategy: str
    num_buys: int
    total_units: float
    total_spent: float
    average_cost: float
    final_price: float
    final_value: float
    pnl: float
    roi: float
    max_drawdown: float


def _max_drawdown(equity: list[float]) -> float:
    """Worst peak-to-trough decline of an equity curve, as a fraction.

    Args:
        equity: Sequence of portfolio values over time.

    Returns:
        The maximum drawdown in ``[0, 1]``. Returns 0.0 for an empty series or a
        series whose running peak never exceeds zero.
    """
    peak = 0.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            drawdown = (peak - value) / peak
            worst = max(worst, drawdown)
    return worst


def run_backtest(strategy: Strategy, prices: list[float]) -> BacktestResult:
    """Run ``strategy`` over ``prices`` and report the result.

    Args:
        strategy: Any object implementing the
            :class:`~dca_bot.strategies.Strategy` protocol.
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

    # Build the equity curve by replaying buys against the price series so the
    # drawdown reflects how the position's value evolved tick by tick.
    buys_by_tick = {buy.tick: buy for buy in result.buys}
    equity: list[float] = []
    for tick, price in enumerate(prices):
        if tick in buys_by_tick:
            buy = buys_by_tick[tick]
            portfolio.buy(buy.quote_amount, buy.price)
        equity.append(portfolio.value(price))

    final_price = prices[-1]
    final_value = portfolio.value(final_price)
    total_spent = portfolio.cost_basis
    pnl = final_value - total_spent
    roi = pnl / total_spent if total_spent > 0 else 0.0

    return BacktestResult(
        strategy=strategy.name,
        num_buys=len(result.buys),
        total_units=portfolio.units,
        total_spent=total_spent,
        average_cost=portfolio.average_price,
        final_price=final_price,
        final_value=final_value,
        pnl=pnl,
        roi=roi,
        max_drawdown=_max_drawdown(equity),
    )
