# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.2.0] - 2025

### Added
- **Value-averaging strategy** (`ValueAveragingStrategy`): targets a linearly
  growing portfolio value, buying more on dips and less on spikes, with an
  optional per-buy spend cap.
- **Dip-buy strategy** (`DipBuyStrategy`): scales each buy up in proportion to
  the drawdown from the running high, with a configurable multiplier and cap.
- **`Strategy` protocol** and `build_strategy()` factory so DCA, value-averaging
  and dip-buy can be backtested and reported interchangeably.
- **Multi-asset portfolios** (`MultiAssetPortfolio`): per-symbol holdings with
  aggregate cost basis, value, PnL and value-weighted allocations.
- **Performance reports** (`AssetReport`, `PortfolioReport`): average cost vs.
  market price, cost advantage, ROI and max drawdown, with a capital-weighted
  portfolio roll-up.
- **Typed configuration** (`BotConfig`, `AssetConfig`) loadable from JSON, plus
  an `example_config()` covering all three strategies.
- **Max drawdown** added to backtest results via a replayed equity curve.
- **New CLI subcommands**: `backtest`, `report` (multi-asset from a config) and
  `init-config`, alongside the existing `demo` and `version`.

### Changed
- `run_backtest` now accepts any object implementing the `Strategy` protocol and
  reports the strategy name and max drawdown.

## [0.1.0] - 2025

### Added
- Initial release of dca-bot: Dollar-cost-averaging (DCA) bot with scheduling and backtest.
