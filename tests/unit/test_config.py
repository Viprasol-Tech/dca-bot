from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from dca_bot.config import AssetConfig, BotConfig, example_config
from dca_bot.strategies import DipBuyStrategy, ValueAveragingStrategy


def test_asset_config_normalizes_symbol() -> None:
    asset = AssetConfig(symbol="  btc ", amount=100.0)
    assert asset.symbol == "BTC"


def test_asset_config_builds_correct_strategy() -> None:
    va = AssetConfig(symbol="SOL", strategy="value-averaging", amount=75.0, max_buy=300.0)
    assert isinstance(va.build(), ValueAveragingStrategy)
    dip = AssetConfig(symbol="ETH", strategy="dip-buy", amount=50.0, dip_multiplier=3.0)
    built = dip.build()
    assert isinstance(built, DipBuyStrategy)
    assert built.dip_multiplier == pytest.approx(3.0)


def test_asset_config_validation() -> None:
    with pytest.raises(ValidationError):
        AssetConfig(symbol="BTC", amount=0)
    with pytest.raises(ValidationError):
        AssetConfig(symbol="BTC", amount=100, interval=0)
    with pytest.raises(ValidationError):
        AssetConfig(symbol="BTC", amount=100, strategy="bogus")  # type: ignore[arg-type]


def test_bot_config_rejects_duplicate_symbols() -> None:
    with pytest.raises(ValidationError):
        BotConfig(
            assets=[
                AssetConfig(symbol="BTC", amount=100),
                AssetConfig(symbol="btc", amount=50),
            ]
        )


def test_bot_config_requires_at_least_one_asset() -> None:
    with pytest.raises(ValidationError):
        BotConfig(assets=[])


def test_config_json_round_trip(tmp_path: Path) -> None:
    cfg = example_config()
    path = tmp_path / "cfg.json"
    cfg.save(path)
    loaded = BotConfig.load(path)
    assert loaded.quote_currency == cfg.quote_currency
    assert [a.symbol for a in loaded.assets] == [a.symbol for a in cfg.assets]
    assert loaded == cfg


def test_from_json_parses_text() -> None:
    text = '{"quote_currency": "USD", "assets": [{"symbol": "BTC", "amount": 25}]}'
    cfg = BotConfig.from_json(text)
    assert cfg.quote_currency == "USD"
    assert cfg.assets[0].symbol == "BTC"
    assert cfg.assets[0].strategy == "dca"


def test_example_config_is_valid() -> None:
    cfg = example_config()
    assert len(cfg.assets) == 3
    assert {a.strategy for a in cfg.assets} == {"dca", "dip-buy", "value-averaging"}
