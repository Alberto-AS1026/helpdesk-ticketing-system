import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def setup_logging() -> None:
    """Configura el logger 'helpdesk': consola y archivo con rotación."""
    logger = logging.getLogger("helpdesk")
    if logger.handlers:  # evita duplicar handlers al recargar
        return

    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "helpdesk.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
