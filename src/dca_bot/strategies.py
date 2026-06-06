"""Accumulation strategy variants beyond plain dollar-cost averaging.

This module builds on :class:`~dca_bot.dca.DCAStrategy` and adds two widely
used variants:

* :class:`ValueAveragingStrategy` — instead of spending a fixed amount, it
  targets a portfolio *value* that grows by a fixed step each interval and buys
  exactly enough to reach that target (buying more when price is low and less
  when price is high).
* :class:`DipBuyStrategy` — a DCA variant that scales each buy up when price is
  in drawdown relative to a recent high, accumulating faster during dips.

All strategies share the :class:`Strategy` protocol so they can be backtested,
reported on, and run through the CLI interchangeably.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dca_bot.dca import Buy, DCAResult, DCAStrategy, average_cost_basis

__all__ = [
    "DipBuyStrategy",
    "Strategy",
    "ValueAveragingStrategy",
    "build_strategy",
]


@runtime_checkable
class Strategy(Protocol):
    """Protocol implemented by every accumulation strategy.

    A strategy turns a price series into a :class:`~dca_bot.dca.DCAResult`. The
    only required surface is a human-readable :attr:`name` and a :meth:`run`
    method; how each buy is sized is the strategy's own concern.
    """

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        ...

    def run(self, prices: list[float]) -> DCAResult:
        """Run the strategy over ``prices`` and return the accumulation result."""
        ...


def _summarise(buys: list[Buy]) -> DCAResult:
    """Aggregate a list of buys into a :class:`DCAResult`."""
    total_spent = sum(b.quote_amount for b in buys)
    total_units = sum(b.units for b in buys)
    average_cost = average_cost_basis(total_spent, total_units) if total_units > 0 else 0.0
    return DCAResult(
        buys=buys,
        total_spent=total_spent,
        total_units=total_units,
        average_cost=average_cost,
    )


class ValueAveragingStrategy:
    """Buy enough each interval to hit a linearly growing target value.

    Value averaging sets a target portfolio value that increases by
    ``value_step`` on each buy tick. On every buy tick the strategy computes the
    gap between the current mark-to-market value of the holdings and the target,
    and buys exactly enough units to close a positive gap. When the holdings are
    already at or above target (e.g. after a price spike) the strategy makes no
    buy on that tick — it never sells.

    Args:
        value_step: Quote-currency increment added to the target value on each
            buy tick. Must be > 0.
        interval: Number of ticks between buy decisions. Must be >= 1.
        max_buy: Optional cap on the quote amount spent on any single buy. Must
            be > 0 when provided. Useful to bound spend during deep drawdowns.

    Raises:
        ValueError: If ``value_step <= 0``, ``interval < 1`` or
            ``max_buy <= 0``.
    """

    def __init__(
        self,
        value_step: float,
        interval: int = 1,
        max_buy: float | None = None,
    ) -> None:
        if value_step <= 0:
            raise ValueError("value_step must be positive")
        if interval < 1:
            raise ValueError("interval must be >= 1")
        if max_buy is not None and max_buy <= 0:
            raise ValueError("max_buy must be positive")
        self.value_step = float(value_step)
        self.interval = int(interval)
        self.max_buy = float(max_buy) if max_buy is not None else None

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        return "value-averaging"

    def run(self, prices: list[float]) -> DCAResult:
        """Run value averaging over ``prices``.

        Args:
            prices: Sequence of positive unit prices, one per tick.

        Returns:
            A :class:`~dca_bot.dca.DCAResult` with the executed buys.

        Raises:
            ValueError: If ``prices`` is empty or contains a non-positive price.
        """
        if not prices:
            raise ValueError("prices must not be empty")
        buys: list[Buy] = []
        units_held = 0.0
        target = 0.0
        for tick, price in enumerate(prices):
            if price <= 0:
                raise ValueError("price must be positive")
            if tick % self.interval != 0:
                continue
            target += self.value_step
            current_value = units_held * price
            gap = target - current_value
            if gap <= 0:
                continue
            if self.max_buy is not None:
                gap = min(gap, self.max_buy)
            units = gap / price
            units_held += units
            buys.append(Buy(tick=tick, price=price, quote_amount=gap, units=units))
        return _summarise(buys)


class DipBuyStrategy:
    """DCA that buys more when price is in drawdown from a running high.

    On each buy tick the strategy computes the drawdown of the current price
    relative to the highest price seen so far. The base quote amount is scaled
    up in proportion to that drawdown:

        ``spend = base * (1 + dip_multiplier * drawdown)``

    where ``drawdown`` is a fraction in ``[0, 1)``. With ``dip_multiplier = 0``
    this is identical to plain DCA; larger values accumulate more aggressively
    during dips.

    Args:
        base_amount: Quote currency for a buy at the running high. Must be > 0.
        interval: Number of ticks between buys. Must be >= 1.
        dip_multiplier: How strongly to scale buys with drawdown. Must be >= 0.
        max_multiple: Cap on the scale factor so a single buy cannot exceed
            ``base_amount * max_multiple``. Must be >= 1.

    Raises:
        ValueError: If any argument is out of range.
    """

    def __init__(
        self,
        base_amount: float,
        interval: int = 1,
        dip_multiplier: float = 2.0,
        max_multiple: float = 5.0,
    ) -> None:
        if base_amount <= 0:
            raise ValueError("base_amount must be positive")
        if interval < 1:
            raise ValueError("interval must be >= 1")
        if dip_multiplier < 0:
            raise ValueError("dip_multiplier must be non-negative")
        if max_multiple < 1:
            raise ValueError("max_multiple must be >= 1")
        self.base_amount = float(base_amount)
        self.interval = int(interval)
        self.dip_multiplier = float(dip_multiplier)
        self.max_multiple = float(max_multiple)

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        return "dip-buy"

    def spend_for(self, price: float, running_high: float) -> float:
        """Quote amount to spend at ``price`` given the ``running_high``.

        Args:
            price: Current unit price. Must be > 0.
            running_high: Highest price seen so far. Must be > 0.

        Returns:
            The (capped) quote amount to spend on this buy.

        Raises:
            ValueError: If ``price`` or ``running_high`` is non-positive.
        """
        if price <= 0:
            raise ValueError("price must be positive")
        if running_high <= 0:
            raise ValueError("running_high must be positive")
        drawdown = max(0.0, (running_high - price) / running_high)
        scale = 1.0 + self.dip_multiplier * drawdown
        scale = min(scale, self.max_multiple)
        return self.base_amount * scale

    def run(self, prices: list[float]) -> DCAResult:
        """Run dip-buying over ``prices``.

        Args:
            prices: Sequence of positive unit prices, one per tick.

        Returns:
            A :class:`~dca_bot.dca.DCAResult` with the executed buys.

        Raises:
            ValueError: If ``prices`` is empty or contains a non-positive price.
        """
        if not prices:
            raise ValueError("prices must not be empty")
        buys: list[Buy] = []
        running_high = 0.0
        for tick, price in enumerate(prices):
            if price <= 0:
                raise ValueError("price must be positive")
            running_high = max(running_high, price)
            if tick % self.interval != 0:
                continue
            spend = self.spend_for(price, running_high)
            units = spend / price
            buys.append(Buy(tick=tick, price=price, quote_amount=spend, units=units))
        return _summarise(buys)


def build_strategy(
    kind: str,
    amount: float,
    interval: int = 1,
    *,
    dip_multiplier: float = 2.0,
    max_multiple: float = 5.0,
    max_buy: float | None = None,
) -> Strategy:
    """Construct a strategy by name.

    Args:
        kind: One of ``"dca"``, ``"value-averaging"`` (alias ``"value"``) or
            ``"dip-buy"`` (alias ``"dip"``).
        amount: Per-interval quote amount (DCA / dip base) or value step (VA).
        interval: Ticks between buys.
        dip_multiplier: Drawdown sensitivity for the dip-buy strategy.
        max_multiple: Per-buy scale cap for the dip-buy strategy.
        max_buy: Optional per-buy spend cap for value averaging.

    Returns:
        A configured strategy implementing the :class:`Strategy` protocol.

    Raises:
        ValueError: If ``kind`` is unknown.
    """
    normalized = kind.strip().lower()
    if normalized == "dca":
        return DCAStrategy(quote_amount=amount, interval=interval)
    if normalized in {"value-averaging", "value", "va"}:
        return ValueAveragingStrategy(value_step=amount, interval=interval, max_buy=max_buy)
    if normalized in {"dip-buy", "dip"}:
        return DipBuyStrategy(
            base_amount=amount,
            interval=interval,
            dip_multiplier=dip_multiplier,
            max_multiple=max_multiple,
        )
    raise ValueError(f"unknown strategy kind: {kind!r}")
