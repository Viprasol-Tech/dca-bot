"""Command-line interface for DCA Bot.

``dca-bot demo`` runs a dollar-cost-averaging backtest on a synthetic price
series — no API keys, no risk.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math

import typer
from rich.console import Console

from dca_bot import __version__
from dca_bot.backtest import run_backtest
from dca_bot.dca import DCAStrategy

app = typer.Typer(add_completion=False, help="DCA Bot — by Viprasol Tech.")
console = Console()


def _synthetic_prices(n: int = 200, base: float = 100.0) -> list[float]:
    """Generate a deterministic wavy synthetic price series."""
    return [base + 15.0 * math.sin(i / 10.0) for i in range(n)]


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"dca-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def demo(
    quote_amount: float = typer.Option(100.0, help="Quote currency to buy each interval."),
    interval: int = typer.Option(5, help="Ticks between buys."),
) -> None:
    """Run a DCA backtest on synthetic data."""
    if quote_amount <= 0:
        console.print("[red]quote-amount must be positive[/]")
        raise typer.Exit(code=1)
    if interval < 1:
        console.print("[red]interval must be >= 1[/]")
        raise typer.Exit(code=1)

    prices = _synthetic_prices()
    strategy = DCAStrategy(quote_amount=quote_amount, interval=interval)
    result = run_backtest(strategy, prices)

    console.print(f"Strategy:      [bold]{strategy.name}[/]")
    console.print(f"Buys:          {result.num_buys} (every {interval} ticks)")
    console.print(f"Total spent:   ${result.total_spent:,.2f}")
    console.print(f"Units held:    {result.total_units:,.4f}")
    console.print(f"Average cost:  ${result.average_cost:,.4f}")
    console.print(f"Final price:   ${result.final_price:,.4f}")
    console.print(f"Final value:   [bold green]${result.final_value:,.2f}[/]")
    console.print(f"PnL:           ${result.pnl:,.2f} ({result.roi:+.2%})")


if __name__ == "__main__":
    app()
