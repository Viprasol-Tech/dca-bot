"""DCA Bot — dollar-cost-averaging bot with scheduling and backtest by Viprasol Tech."""

from __future__ import annotations

from dca_bot.backtest import BacktestResult, run_backtest
from dca_bot.config import AssetConfig, BotConfig, example_config
from dca_bot.dca import Buy, DCAResult, DCAStrategy, average_cost_basis
from dca_bot.portfolio import MultiAssetPortfolio, Portfolio
from dca_bot.report import AssetReport, PortfolioReport, report_portfolio, report_strategy
from dca_bot.strategies import (
    DipBuyStrategy,
    Strategy,
    ValueAveragingStrategy,
    build_strategy,
)

__version__ = "0.2.0"
__author__ = "Viprasol Tech Private Limited"
__all__ = [
    "AssetConfig",
    "AssetReport",
    "BacktestResult",
    "BotConfig",
    "Buy",
    "DCAResult",
    "DCAStrategy",
    "DipBuyStrategy",
    "MultiAssetPortfolio",
    "Portfolio",
    "PortfolioReport",
    "Strategy",
    "ValueAveragingStrategy",
    "__version__",
    "average_cost_basis",
    "build_strategy",
    "example_config",
    "report_portfolio",
    "report_strategy",
    "run_backtest",
]
