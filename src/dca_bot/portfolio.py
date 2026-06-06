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


class MultiAssetPortfolio:
    """Track many single-asset :class:`Portfolio` holdings keyed by symbol.

    Each symbol gets its own sub-portfolio, created lazily on first buy. The
    aggregate cost basis, value and PnL are simple sums across the holdings.

    Args:
        symbols: Optional symbols to pre-create with empty holdings.
    """

    def __init__(self, symbols: list[str] | None = None) -> None:
        self._holdings: dict[str, Portfolio] = {}
        for symbol in symbols or []:
            self._holdings[self._normalize(symbol)] = Portfolio()

    @staticmethod
    def _normalize(symbol: str) -> str:
        """Normalise a symbol to a non-empty upper-case key."""
        key = symbol.strip().upper()
        if not key:
            raise ValueError("symbol must not be empty")
        return key

    @property
    def symbols(self) -> list[str]:
        """Symbols currently tracked, in insertion order."""
        return list(self._holdings)

    def holding(self, symbol: str) -> Portfolio:
        """Return the sub-portfolio for ``symbol``, creating it if needed.

        Args:
            symbol: Asset symbol (case-insensitive).

        Returns:
            The :class:`Portfolio` for that symbol.
        """
        key = self._normalize(symbol)
        if key not in self._holdings:
            self._holdings[key] = Portfolio()
        return self._holdings[key]

    def buy(self, symbol: str, quote_amount: float, price: float) -> float:
        """Buy ``symbol`` for ``quote_amount`` at ``price``.

        Args:
            symbol: Asset symbol (case-insensitive).
            quote_amount: Quote currency to spend. Must be > 0.
            price: Unit price. Must be > 0.

        Returns:
            The units acquired by this buy.
        """
        return self.holding(symbol).buy(quote_amount, price)

    def cost_basis(self) -> float:
        """Total quote currency spent across every holding."""
        return sum(p.cost_basis for p in self._holdings.values())

    def value(self, prices: dict[str, float]) -> float:
        """Aggregate mark-to-market value at the supplied ``prices``.

        Args:
            prices: Mapping of symbol to current unit price. Every tracked
                symbol with units must be present.

        Returns:
            The summed value of all holdings.

        Raises:
            KeyError: If a held symbol is missing from ``prices``.
        """
        priced = {self._normalize(s): p for s, p in prices.items()}
        total = 0.0
        for key, holding in self._holdings.items():
            if holding.units <= 0:
                continue
            if key not in priced:
                raise KeyError(f"missing price for {key}")
            total += holding.value(priced[key])
        return total

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        """Aggregate unrealised PnL at the supplied ``prices``."""
        return self.value(prices) - self.cost_basis()

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        """Value-weighted allocation of each held symbol.

        Args:
            prices: Mapping of symbol to current unit price.

        Returns:
            Mapping of symbol to its fraction of total value. Empty when the
            portfolio has no value.
        """
        total = self.value(prices)
        if total <= 0:
            return {}
        priced = {self._normalize(s): p for s, p in prices.items()}
        return {
            key: holding.value(priced[key]) / total
            for key, holding in self._holdings.items()
            if holding.units > 0
        }
