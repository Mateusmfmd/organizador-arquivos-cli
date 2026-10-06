"""Interface de linha de comando do organizador."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import ConfigError, load_config
from .logging_utils import configure_logging
from .organizer import FileOrganizer, OrganizationError, OrganizationSummary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="organizar-arquivos",
        description="Organiza arquivos de uma pasta por extensão/categoria.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Pasta a organizar (padrão: diretório atual).")
    parser.add_argument("--config", metavar="ARQUIVO", help="Arquivo JSON de configuração.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria feito sem mover arquivos.")
    parser.add_argument("--recursive", action="store_true", default=None, help="Inclui subpastas.")
    parser.add_argument(
        "--include-hidden", action="store_true", default=None, help="Inclui arquivos e pastas ocultos."
    )
    parser.add_argument(
        "--conflict-strategy",
        choices=("rename", "skip", "overwrite"),
        default=None,
        help="Estratégia quando o destino já existe (padrão: rename).",
    )
    parser.add_argument("--log-file", metavar="ARQUIVO", help="Também grava logs neste arquivo.")
    parser.add_argument("--json", action="store_true", help="Emite o resumo completo como JSON.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Ativa logs detalhados.")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _summary_text(summary: OrganizationSummary) -> str:
    mode = "simulação" if summary.dry_run else "execução"
    lines = [
        f"Organização ({mode}) concluída: {summary.source}",
        f"Planejados: {summary.planned} | Movidos: {summary.moved} | "
        f"Ignorados: {summary.skipped} | Erros: {summary.errors}",
    ]
    if summary.error_details:
        lines.append("Detalhes dos erros:")
        lines.extend(f"- {detail}" for detail in summary.error_details)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.recursive is not None:
            config.recursive = args.recursive
        if args.include_hidden is not None:
            config.include_hidden = args.include_hidden
        if args.conflict_strategy is not None:
            config.conflict_strategy = args.conflict_strategy
        logger = configure_logging(verbose=args.verbose, log_file=args.log_file)
        summary = FileOrganizer(
            Path(args.path),
            config,
            dry_run=args.dry_run,
            logger=logger.log,
        ).organize()
    except (ConfigError, OrganizationError, OSError) as exc:
        # Erros de configuração/entrada são distintos de falhas parciais reportadas no resumo.
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary.to_mapping(), ensure_ascii=False, indent=2))
    else:
        print(_summary_text(summary))
    return 1 if summary.errors else 0
