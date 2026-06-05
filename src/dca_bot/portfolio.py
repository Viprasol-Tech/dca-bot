"""Portfolio accounting for accumulated units and cost basis.

Tracks total units held, the total quote currency spent (cost basis) and the
derived average price. Marking the portfolio to a current price yields its
value and unrealised profit/loss.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dca_bot.dca import average_cost_basis


class Portfolio:
    """Track units held and the quote currency spent to acquire them.

    Args:
        units: Initial units held. Must be >= 0.
        cost_basis: Initial quote currency spent. Must be >= 0.

    Raises:
        ValueError: If ``units`` or ``cost_basis`` is negative.
    """

    def __init__(self, units: float = 0.0, cost_basis: float = 0.0) -> None:
        if units < 0:
            raise ValueError("units must be non-negative")
        if cost_basis < 0:
            raise ValueError("cost_basis must be non-negative")
        self.units = float(units)
        self.cost_basis = float(cost_basis)

    def buy(self, quote_amount: float, price: float) -> float:
        """Spend ``quote_amount`` at ``price`` and accumulate units.

        Args:
            quote_amount: Quote currency to spend. Must be > 0.
            price: Unit price. Must be > 0.

        Returns:
            The units acquired by this buy.

        Raises:
            ValueError: If ``quote_amount <= 0`` or ``price <= 0``.
        """
        if quote_amount <= 0:
            raise ValueError("quote_amount must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        units = quote_amount / price
        self.units += units
        self.cost_basis += quote_amount
        return units

    @property
    def average_price(self) -> float:
        """Average quote currency paid per unit, or 0.0 when no units are held."""
        if self.units <= 0:
            return 0.0
        return average_cost_basis(self.cost_basis, self.units)

    def value(self, price: float) -> float:
        """Mark-to-market value of the holdings at ``price``.

        Args:
            price: Current unit price. Must be >= 0.

        Returns:
            ``units * price``.

        Raises:
            ValueError: If ``price`` is negative.
        """
        if price < 0:
            raise ValueError("price must be non-negative")
        return self.units * price

    def unrealized_pnl(self, price: float) -> float:
        """Unrealised profit/loss at ``price``.

        Args:
            price: Current unit price. Must be >= 0.

        Returns:
            ``value(price) - cost_basis``.

        Raises:
            ValueError: If ``price`` is negative.
        """
        return self.value(price) - self.cost_basis
