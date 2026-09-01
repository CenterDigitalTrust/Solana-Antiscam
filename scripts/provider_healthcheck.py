"""
Standalone Provider Healthcheck Script.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.healthcheck import print_table, run_healthcheck

if __name__ == "__main__":
    results = run_healthcheck()
    print_table(results)
