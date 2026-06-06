from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dca_bot import __version__
from dca_bot.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_demo_command_runs() -> None:
    result = runner.invoke(app, ["demo", "--interval", "5", "--quote-amount", "100"])
    assert result.exit_code == 0
    assert "Strategy:" in result.stdout
    assert "Max drawdown:" in result.stdout


def test_demo_rejects_bad_args() -> None:
    result = runner.invoke(app, ["demo", "--quote-amount", "0"])
    assert result.exit_code == 1


def test_backtest_command_value_averaging() -> None:
    result = runner.invoke(app, ["backtest", "--strategy", "value-averaging", "--amount", "100"])
    assert result.exit_code == 0
    assert "value-averaging" in result.stdout


def test_backtest_command_unknown_strategy() -> None:
    result = runner.invoke(app, ["backtest", "--strategy", "nope"])
    assert result.exit_code == 1


def test_init_config_and_report_roundtrip(tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg.json"
    written = runner.invoke(app, ["init-config", "--path", str(cfg_path)])
    assert written.exit_code == 0
    assert cfg_path.exists()

    # Refuses to overwrite without --force.
    again = runner.invoke(app, ["init-config", "--path", str(cfg_path)])
    assert again.exit_code == 1

    reported = runner.invoke(app, ["report", "--config", str(cfg_path)])
    assert reported.exit_code == 0
    assert "Portfolio ROI:" in reported.stdout
