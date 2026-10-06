"""Configuração de logging sem dependências externas."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "organizador_arquivos"


def configure_logging(*, verbose: bool = False, log_file: str | Path | None = None) -> logging.Logger:
    """Configura handlers determinísticos para evitar mensagens duplicadas em chamadas repetidas."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        path = Path(log_file).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(path, encoding="utf-8")
        except OSError as exc:
            raise OSError(f"Não foi possível abrir o arquivo de log {path}: {exc}") from exc
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
