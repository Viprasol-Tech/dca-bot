"""Dollar-cost-averaging strategy and accumulation math.

A DCA strategy buys a fixed *quote* amount (e.g. 100 USDT) every ``interval``
ticks of a price series, regardless of price. This module exposes the strategy
itself plus pure helpers to compute the units accumulated and the average cost
basis over a price series.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Buy:
    """A single executed DCA buy.

    Attributes:
        tick: Zero-based index in the price series at which the buy occurred.
        price: Unit price paid (quote currency per unit).
        quote_amount: Amount of quote currency spent on this buy.
        units: Units purchased, equal to ``quote_amount / price``.
    """

    tick: int
    price: float
    quote_amount: float
    units: float


@dataclass(frozen=True)
class DCAResult:
    """Aggregate outcome of running a DCA strategy over a price series.

    Attributes:
        buys: The individual buys that were executed, in order.
        total_spent: Total quote currency spent across all buys.
        total_units: Total units accumulated across all buys.
        average_cost: Quote currency paid per unit (``total_spent / total_units``).
    """

    buys: list[Buy]
    total_spent: float
    total_units: float
    average_cost: float


class DCAStrategy:
    """Buy a fixed quote amount every ``interval`` ticks.

    The strategy is stateless with respect to price: on every tick whose index
    is a multiple of ``interval`` it spends exactly ``quote_amount`` of quote
    currency at the current price.

    Args:
        quote_amount: Quote currency to spend on each buy. Must be > 0.
        interval: Number of ticks between buys. Must be >= 1. A buy fires on
            ticks ``0, interval, 2 * interval, ...``.

    Raises:
        ValueError: If ``quote_amount <= 0`` or ``interval < 1``.
    """

    def __init__(self, quote_amount: float, interval: int) -> None:
        if quote_amount <= 0:
            raise ValueError("quote_amount must be positive")
        if interval < 1:
            raise ValueError("interval must be >= 1")
        self.quote_amount = float(quote_amount)
        self.interval = int(interval)

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        return "dca"

    def should_buy(self, tick: int) -> bool:
        """Return whether a buy fires on ``tick``.

        Args:
            tick: Zero-based index into the price series. Must be >= 0.

        Returns:
            ``True`` if ``tick`` is a multiple of ``interval``.

        Raises:
            ValueError: If ``tick`` is negative.
        """
        if tick < 0:
            raise ValueError("tick must be non-negative")
        return tick % self.interval == 0

    def buy_at(self, tick: int, price: float) -> Buy:
        """Build the :class:`Buy` for a tick where a buy fires.

        Args:
            tick: Zero-based index into the price series.
            price: Unit price at ``tick``. Must be > 0.

        Returns:
            The executed :class:`Buy`.

        Raises:
            ValueError: If ``price <= 0``.
        """
        if price <= 0:
            raise ValueError("price must be positive")
        units = self.quote_amount / price
        return Buy(tick=tick, price=price, quote_amount=self.quote_amount, units=units)

    def run(self, prices: list[float]) -> DCAResult:
        """Run the strategy over a price series and accumulate units.

        Args:
            prices: Sequence of positive unit prices, one per tick.

        Returns:
            A :class:`DCAResult` with the buys and aggregate cost basis.

        Raises:
            ValueError: If ``prices`` is empty or contains a non-positive price.
        """
        if not prices:
            raise ValueError("prices must not be empty")
        buys: list[Buy] = []
        for tick, price in enumerate(prices):
            if self.should_buy(tick):
                buys.append(self.buy_at(tick, price))
        total_spent = sum(b.quote_amount for b in buys)
        total_units = sum(b.units for b in buys)
        average_cost = average_cost_basis(total_spent, total_units)
        return DCAResult(
            buys=buys,
            total_spent=total_spent,
            total_units=total_units,
            average_cost=average_cost,
        )


def average_cost_basis(total_spent: float, total_units: float) -> float:
    """Compute average cost per unit.

    Args:
        total_spent: Total quote currency spent.
        total_units: Total units accumulated. Must be > 0.

    Returns:
        ``total_spent / total_units``.

    Raises:
        ValueError: If ``total_units <= 0``.
    """
    if total_units <= 0:
        raise ValueError("total_units must be positive")
    return total_spent / total_units
