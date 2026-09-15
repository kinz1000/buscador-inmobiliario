import logging

from src.config import BASE_DIR


LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "bot.log"


def setup_logging() -> None:
    LOGS_DIR.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(
                LOG_FILE,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )