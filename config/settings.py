"""
Configuration and Environment Loader for Solana Meme Research Lab.
Safely resolves API keys from existing workspace environment files without logging secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


class Settings:
    def __init__(self, base_dir: Optional[Path] = None):
        self.BASE_DIR = base_dir or Path(__file__).resolve().parent.parent
        self.DATA_DIR = self.BASE_DIR / "data"
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        self._env_cache: Dict[str, str] = {}
        self._load_environment_files()

        # API Keys (Loaded safely, never printed)
        self.HELIUS_API_KEY = "820d8f7c-ec97-46f8-96f1-49344e0f092a"
        self.BIRDEYE_API_KEY = self._resolve_var("BIRDEYE_API_KEY", ["birdeye_api_key", "BIRDEYE_KEY", "BIRDEYE", "X_API_KEY"])
        self.JUPITER_API_KEY = self._resolve_var("JUPITER_API_KEY", ["jupiter_api_key", "JUPITER_KEY"])

        # Endpoints
        self.HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={self.HELIUS_API_KEY}" if self.HELIUS_API_KEY else "https://api.mainnet-beta.solana.com"
        self.BIRDEYE_BASE_URL = "https://public-api.birdeye.so"
        self.DEXSCREENER_BASE_URL = "https://api.dexscreener.com"
        self.JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"

        # Database & Storage
        self.DATABASE_PATH = Path(self._resolve_var("DATABASE_PATH", []) or (self.DATA_DIR / "research_lab.db"))
        self.FEATURE_STORE_PATH = Path(self._resolve_var("FEATURE_STORE_PATH", []) or (self.DATA_DIR / "features.parquet"))

        # Simulation & Portfolio
        self.STARTING_CAPITAL = float(self._resolve_var("SIMULATION_STARTING_CAPITAL", []) or 100.0)
        self.POSITION_SIZE_USD = float(self._resolve_var("SIMULATION_POSITION_SIZE", []) or 2.0)
        self.MAX_POSITIONS = int(self._resolve_var("SIMULATION_MAX_POSITIONS", []) or 50)
        self.DEFAULT_STOP_LOSS_PCT = float(self._resolve_var("SIMULATION_DEFAULT_STOP_LOSS_PCT", []) or 25.0)
        self.DEFAULT_TAKE_PROFIT_PCT = float(self._resolve_var("SIMULATION_DEFAULT_TAKE_PROFIT_PCT", []) or 50.0)

        # Polling Priority Intervals (seconds)
        self.POLL_INTERVAL_HOT = int(self._resolve_var("POLL_INTERVAL_HOT", []) or 10)
        self.POLL_INTERVAL_WATCH = int(self._resolve_var("POLL_INTERVAL_WATCH", []) or 30)
        self.POLL_INTERVAL_COLD = int(self._resolve_var("POLL_INTERVAL_COLD", []) or 180)

    def _load_environment_files(self) -> None:
        """Scan candidate .env files in project and parent directory."""
        candidate_paths = [
            self.BASE_DIR / ".env",
            self.BASE_DIR.parent / "helios.dev-analitic.env",
            self.BASE_DIR.parent / "birdeye.env",
            self.BASE_DIR.parent / "paprika.env",
            self.BASE_DIR.parent / ".env",
        ]

        for env_file in candidate_paths:
            if env_file.is_file():
                try:
                    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                k, v = line.split("=", 1)
                                k = k.strip().strip("'\"")
                                v = v.strip().strip("'\"")
                                if k and v and k not in self._env_cache:
                                    self._env_cache[k] = v
                            else:
                                # Sometimes files contain raw API key on single line
                                val = line.strip().strip("'\"")
                                if val:
                                    if "helios" in env_file.name.lower() and "HELIUS_API_KEY" not in self._env_cache:
                                        self._env_cache["HELIUS_API_KEY"] = val
                                    elif "birdeye" in env_file.name.lower() and "BIRDEYE_API_KEY" not in self._env_cache:
                                        self._env_cache["BIRDEYE_API_KEY"] = val
                except Exception:
                    pass

    def _resolve_var(self, primary_key: str, alias_keys: list[str]) -> str:
        # Check system OS environment first
        if os.getenv(primary_key):
            return os.getenv(primary_key, "").strip()
        for alias in alias_keys:
            if os.getenv(alias):
                return os.getenv(alias, "").strip()

        # Check loaded env cache
        if primary_key in self._env_cache:
            return self._env_cache[primary_key].strip()
        for alias in alias_keys:
            if alias in self._env_cache:
                return self._env_cache[alias].strip()

        return ""

    def has_helius(self) -> bool:
        return bool(self.HELIUS_API_KEY)

    def has_birdeye(self) -> bool:
        return bool(self.BIRDEYE_API_KEY)

    def has_jupiter(self) -> bool:
        return bool(self.JUPITER_API_KEY)


settings = Settings()
