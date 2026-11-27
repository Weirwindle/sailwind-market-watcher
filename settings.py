"""Defaults and persisted player inputs for Market Watcher."""

import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

APP_DIR = Path(__file__).resolve().parent
with (APP_DIR / "config.json").open(encoding="utf-8") as file:
    CONFIG = json.load(file)

PLAYER_SETTINGS = CONFIG["player_settings"]
PLAYER_SETTINGS_PATH = (
    Path(os.environ.get("LOCALAPPDATA") or Path.home())
    / "SailwindMarketWatcher"
    / "player-settings.json"
)


def load_player_settings(path):
    settings = PLAYER_SETTINGS.copy()
    try:
        with path.open(encoding="utf-8") as file:
            saved_settings = json.load(file)
    except (OSError, ValueError):
        return settings

    if isinstance(saved_settings, dict):
        for key in settings:
            value = saved_settings.get(key)
            if type(value) in (int, float) and abs(value) < math.inf:
                settings[key] = value
    return settings


def save_player_settings(path, settings):
    path.parent.mkdir(parents=True, exist_ok=True)
    file = NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    temporary_path = Path(file.name)
    try:
        with file:
            json.dump(settings, file, indent=2, allow_nan=False)
            file.write("\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


class Player:
    def __init__(self):
        self.update(**load_player_settings(PLAYER_SETTINGS_PATH))

    def update(self, principal, conversion_rate, mass_limit, volume_limit, min_profit):
        self.principal = principal
        self.conversion_rate = conversion_rate
        self.mass_limit = mass_limit
        self.volume_limit = volume_limit
        self.min_profit = min_profit

    def __repr__(self):
        # Print float values without decimals
        return (
            f"Player:\n Principal: {self.principal:.0f}\n Currency: {self.conversion_rate}\n "
            f"Mass: {self.mass_limit:.0f}\n Volume: {self.volume_limit:.0f}"
        )
