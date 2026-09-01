"""
Base Analyzer Interface for Solana Meme Research Lab.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
