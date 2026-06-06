"""Command-line interface for DCA Bot.

Subcommands:

* ``dca-bot demo`` — run a backtest on a synthetic price series (no keys, no risk).
* ``dca-bot backtest`` — backtest one strategy (dca / value-averaging / dip-buy).
* ``dca-bot report`` — backtest a whole multi-asset config and print a roll-up.
* ``dca-bot init-config`` — write a ready-to-edit example config file.
* ``dca-bot version`` — print the installed version.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dca_bot import __version__
from dca_bot.backtest import run_backtest
from dca_bot.config import BotConfig, example_config
from dca_bot.report import AssetReport, PortfolioReport, report_portfolio, report_strategy
from dca_bot.strategies import build_strategy

app = typer.Typer(add_completion=False, help="DCA Bot — by Viprasol Tech.")
console = Console()


def _synthetic_prices(n: int = 200, base: float = 100.0, amplitude: float = 15.0) -> list[float]:
    """Generate a deterministic wavy synthetic price series."""
    return [base + amplitude * math.sin(i / 10.0) for i in range(n)]


def _print_asset_report(report: AssetReport) -> None:
    """Render a single :class:`AssetReport` to the console."""
    console.print(f"Symbol:           [bold]{report.symbol}[/]")
    console.print(f"Strategy:         [bold]{report.strategy}[/]")
    console.print(f"Total spent:      ${report.total_spent:,.2f}")
    console.print(f"Units held:       {report.total_units:,.4f}")
    console.print(f"Average cost:     ${report.average_cost:,.4f}")
    console.print(f"Market price:     ${report.market_price:,.4f}")
    console.print(f"Cost advantage:   {report.cost_advantage:+.2%}")
    console.print(f"Final value:      [bold green]${report.final_value:,.2f}[/]")
    console.print(f"ROI:              {report.roi:+.2%}")
    console.print(f"Max drawdown:     {report.max_drawdown:.2%}")


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
    strategy = build_strategy("dca", amount=quote_amount, interval=interval)
    result = run_backtest(strategy, prices)

    console.print(f"Strategy:      [bold]{strategy.name}[/]")
    console.print(f"Buys:          {result.num_buys} (every {interval} ticks)")
    console.print(f"Total spent:   ${result.total_spent:,.2f}")
    console.print(f"Units held:    {result.total_units:,.4f}")
    console.print(f"Average cost:  ${result.average_cost:,.4f}")
    console.print(f"Final price:   ${result.final_price:,.4f}")
    console.print(f"Final value:   [bold green]${result.final_value:,.2f}[/]")
    console.print(f"PnL:           ${result.pnl:,.2f} ({result.roi:+.2%})")
    console.print(f"Max drawdown:  {result.max_drawdown:.2%}")


@app.command()
def backtest(
    strategy: str = typer.Option("dca", help="dca | value-averaging | dip-buy."),
    amount: float = typer.Option(100.0, help="Per-buy amount (DCA/dip) or value step (VA)."),
    interval: int = typer.Option(5, help="Ticks between buys."),
    symbol: str = typer.Option("ASSET", help="Symbol label for the report."),
    dip_multiplier: float = typer.Option(2.0, help="Drawdown sensitivity (dip-buy)."),
    max_multiple: float = typer.Option(5.0, help="Per-buy scale cap (dip-buy)."),
) -> None:
    """Backtest one strategy on synthetic data and print a performance report."""
    try:
        strat = build_strategy(
            strategy,
            amount=amount,
            interval=interval,
            dip_multiplier=dip_multiplier,
            max_multiple=max_multiple,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    prices = _synthetic_prices()
    report = report_strategy(symbol, strat, prices)
    _print_asset_report(report)


def _print_portfolio_report(report: PortfolioReport, quote_currency: str) -> None:
    """Render a :class:`PortfolioReport` as a rich table plus a summary."""
    table = Table(title="Portfolio backtest")
    table.add_column("Symbol", style="bold")
    table.add_column("Strategy")
    table.add_column(f"Spent ({quote_currency})", justify="right")
    table.add_column("Avg cost", justify="right")
    table.add_column("Market", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("ROI", justify="right")
    table.add_column("Max DD", justify="right")
    for asset in report.assets:
        table.add_row(
            asset.symbol,
            asset.strategy,
            f"{asset.total_spent:,.2f}",
            f"{asset.average_cost:,.4f}",
            f"{asset.market_price:,.4f}",
            f"{asset.final_value:,.2f}",
            f"{asset.roi:+.2%}",
            f"{asset.max_drawdown:.2%}",
        )
    console.print(table)
    console.print(f"Total spent:   ${report.total_spent:,.2f}")
    console.print(f"Total value:   [bold green]${report.total_value:,.2f}[/]")
    console.print(f"Portfolio ROI: {report.roi:+.2%}")
    console.print(f"Worst drawdown: {report.worst_drawdown:.2%}")


@app.command()
def report(
    config: Path = typer.Option(..., exists=True, help="Path to a JSON bot config."),
) -> None:
    """Backtest every asset in a config on synthetic data and roll up the result."""
    try:
        cfg = BotConfig.load(config)
    except (ValueError, OSError) as exc:
        console.print(f"[red]failed to load config: {exc}[/]")
        raise typer.Exit(code=1) from exc

    # Give each asset a distinct synthetic series so the report is non-trivial.
    series = {
        asset.symbol: _synthetic_prices(amplitude=10.0 + 5.0 * idx)
        for idx, asset in enumerate(cfg.assets)
    }
    result = report_portfolio(cfg, series)
    _print_portfolio_report(result, cfg.quote_currency)


@app.command(name="init-config")
def init_config(
    path: Path = typer.Option(Path("dca-config.json"), help="Where to write the example."),
    force: bool = typer.Option(False, help="Overwrite an existing file."),
) -> None:
    """Write a ready-to-edit example config covering all three strategies."""
    if path.exists() and not force:
        console.print(f"[red]{path} already exists (use --force to overwrite)[/]")
        raise typer.Exit(code=1)
    example_config().save(path)
    console.print(f"Wrote example config to [bold]{path}[/]")


if __name__ == "__main__":
    app()
