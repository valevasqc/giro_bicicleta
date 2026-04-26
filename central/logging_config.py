import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path(__file__).parent / "logs"
_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(module)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    file_level = getattr(logging, os.environ.get("LOG_LEVEL_FILE", "INFO").upper(), logging.INFO)
    console_level = getattr(logging, os.environ.get("LOG_LEVEL_CONSOLE", "INFO").upper(), logging.INFO)

    fh = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "central.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(file_level)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

# tail -f central/logs/central.log | grep -E "RENTAL|RETURN|TOPUP|ERROR"