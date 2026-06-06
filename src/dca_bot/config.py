"""Typed configuration for DCA Bot, loadable from JSON.

A :class:`BotConfig` describes one or more assets to accumulate, each with its
own strategy choice and parameters. Configs are validated by pydantic so bad
values fail fast with a clear message, and can be round-tripped to and from
JSON for storing alongside a project.

Part of DCA Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from dca_bot.strategies import Strategy, build_strategy

StrategyKind = Literal["dca", "value-averaging", "dip-buy"]


class AssetConfig(BaseModel):
    """Configuration for accumulating a single asset.

    Attributes:
        symbol: Asset ticker, normalised to upper case.
        strategy: Which accumulation strategy to use.
        amount: Per-interval quote amount (DCA / dip base) or value step (VA).
        interval: Ticks between buys.
        dip_multiplier: Drawdown sensitivity for the dip-buy strategy.
        max_multiple: Per-buy scale cap for the dip-buy strategy.
        max_buy: Optional per-buy spend cap for value averaging.
    """

    symbol: str = Field(min_length=1)
    strategy: StrategyKind = "dca"
    amount: float = Field(gt=0)
    interval: int = Field(default=1, ge=1)
    dip_multiplier: float = Field(default=2.0, ge=0)
    max_multiple: float = Field(default=5.0, ge=1)
    max_buy: float | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be empty")
        return normalized

    def build(self) -> Strategy:
        """Construct the configured :class:`~dca_bot.strategies.Strategy`."""
        return build_strategy(
            self.strategy,
            amount=self.amount,
            interval=self.interval,
            dip_multiplier=self.dip_multiplier,
            max_multiple=self.max_multiple,
            max_buy=self.max_buy,
        )


class BotConfig(BaseModel):
    """Top-level bot configuration: a quote currency and a list of assets.

    Attributes:
        quote_currency: The currency amounts are denominated in (e.g. USDT).
        assets: One or more :class:`AssetConfig` entries to accumulate.
    """

    quote_currency: str = Field(default="USDT", min_length=1)
    assets: list[AssetConfig] = Field(min_length=1)

    @field_validator("assets")
    @classmethod
    def _unique_symbols(cls, value: list[AssetConfig]) -> list[AssetConfig]:
        seen = [a.symbol for a in value]
        if len(set(seen)) != len(seen):
            raise ValueError("asset symbols must be unique")
        return value

    @classmethod
    def from_json(cls, text: str) -> BotConfig:
        """Parse a config from a JSON string."""
        return cls.model_validate(json.loads(text))

    @classmethod
    def load(cls, path: str | Path) -> BotConfig:
        """Load and validate a config from a JSON file.

        Args:
            path: Path to a JSON config file.

        Returns:
            The validated :class:`BotConfig`.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
        """
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def to_json(self, *, indent: int = 2) -> str:
        """Serialise this config to a JSON string."""
        return self.model_dump_json(indent=indent)

    def save(self, path: str | Path) -> None:
        """Write this config to ``path`` as pretty JSON."""
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")


def example_config() -> BotConfig:
    """A ready-to-edit example config covering all three strategies."""
    return BotConfig(
        quote_currency="USDT",
        assets=[
            AssetConfig(symbol="BTC", strategy="dca", amount=100.0, interval=7),
            AssetConfig(symbol="ETH", strategy="dip-buy", amount=50.0, interval=7),
            AssetConfig(
                symbol="SOL",
                strategy="value-averaging",
                amount=75.0,
                interval=7,
                max_buy=300.0,
            ),
        ],
    )
