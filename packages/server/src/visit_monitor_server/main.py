"""CLI entry point for the PolliPi visit-monitor server.

This module creates the FastAPI ``app`` at module level so that uvicorn
can be pointed at it directly:

    uvicorn visit_monitor_server.main:app --host 0.0.0.0 --port 8000

It also exposes a ``main()`` function for use as a console-scripts entry point.
"""
from __future__ import annotations

import uvicorn  # type: ignore

from visit_monitor_server.app import create_app

# Module-level app instance (required for uvicorn's import syntax)
app = create_app()


def main() -> None:
    """Start the server via the console-scripts entry point."""
    uvicorn.run(
        "visit_monitor_server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
