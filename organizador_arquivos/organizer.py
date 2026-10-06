"""Motor de organização de arquivos, sem dependências externas."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from .config import OrganizerConfig


class OrganizationError(RuntimeError):
    """Erro fatal que impede a organização da pasta de origem."""


@dataclass(slots=True)
class FileOperation:
    source: str
    target: str | None
    action: str
    reason: str | None = None

    def to_mapping(self) -> dict[str, str | None]:
        return {
            "source": self.source,
            "target": self.target,
            "action": self.action,
            "reason": self.reason,
        }


@dataclass(slots=True)
class OrganizationSummary:
    source: str
    dry_run: bool
    planned: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
    operations: list[FileOperation] = field(default_factory=list)

    def to_mapping(self, *, include_operations: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "source": self.source,
            "dry_run": self.dry_run,
            "planned": self.planned,
            "moved": self.moved,
            "skipped": self.skipped,
            "errors": self.errors,
            "error_details": list(self.error_details),
        }
        if include_operations:
            result["operations"] = [operation.to_mapping() for operation in self.operations]
        return result


class FileOrganizer:
    """Organiza arquivos de uma pasta, preservando arquivos de categoria já processados."""

    def __init__(
        self,
        source: str | Path,
        config: OrganizerConfig | None = None,
        *,
        dry_run: bool = False,
        logger: Callable[[int, str], None] | None = None,
    ) -> None:
        self.source = Path(source).expanduser()
        self.config = config or OrganizerConfig()
        self.dry_run = dry_run
        self._logger = logger
        self._category_names = set(self.config.categories) | {self.config.unknown_category}
        self._extension_to_category = {
            extension: category
            for category, extensions in self.config.categories.items()
            for extension in extensions
        }

    def _log(self, level: int, message: str) -> None:
        if self._logger is not None:
            self._logger(level, message)

    def _record_error(self, summary: OrganizationSummary, message: str) -> None:
        summary.errors += 1
        summary.error_details.append(message)
        self._log(40, message)

    def _iter_files(self, summary: OrganizationSummary) -> Iterator[Path]:
        """Percorre arquivos sem seguir links simbólicos e sem entrar nas categorias."""
        if not self.config.recursive:
            try:
                entries = list(self.source.iterdir())
            except OSError as exc:
                self._record_error(summary, f"Não foi possível listar {self.source}: {exc}")
                return
            for entry in entries:
                if entry.name in self.config.ignore or (entry.name.startswith(".") and not self.config.include_hidden):
                    continue
                if entry.is_symlink():
                    summary.skipped += 1
                    summary.operations.append(FileOperation(str(entry), None, "skipped", "link simbólico"))
                    self._log(20, f"Ignorado link simbólico: {entry}")
                elif entry.is_file():
                    yield entry
            return

        def onerror(error: OSError) -> None:
            self._record_error(summary, f"Erro ao percorrer {self.source}: {error}")

        try:
            walker = os.walk(self.source, topdown=True, followlinks=False, onerror=onerror)
            for current, directories, filenames in walker:
                current_path = Path(current)
                retained_directories: list[str] = []
                for directory in directories:
                    candidate = current_path / directory
                    hidden = directory.startswith(".") and not self.config.include_hidden
                    ignored = directory in self.config.ignore or directory in self._category_names
                    if hidden or ignored or candidate.is_symlink():
                        continue
                    retained_directories.append(directory)
                directories[:] = retained_directories
                for filename in filenames:
                    if filename in self.config.ignore or (filename.startswith(".") and not self.config.include_hidden):
                        continue
                    candidate = current_path / filename
                    if candidate.is_symlink():
                        summary.skipped += 1
                        summary.operations.append(FileOperation(str(candidate), None, "skipped", "link simbólico"))
                        self._log(20, f"Ignorado link simbólico: {candidate}")
                    elif candidate.is_file():
                        yield candidate
        except OSError as exc:
            self._record_error(summary, f"Erro ao percorrer {self.source}: {exc}")

    def _category_for(self, path: Path) -> str:
        return self._extension_to_category.get(path.suffix.lower(), self.config.unknown_category)

    @staticmethod
    def _available_target(target: Path) -> Path:
        """Obtém um nome incremental sem sobrescrever arquivo existente."""
        counter = 1
        while True:
            candidate = target.with_name(f"{target.stem} ({counter}){target.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def organize(self) -> OrganizationSummary:
        """Executa a organização e devolve um resumo; erros de um arquivo não abortam os demais."""
        summary = OrganizationSummary(str(self.source), self.dry_run)
        if not self.source.exists():
            raise OrganizationError(f"A pasta de origem não existe: {self.source}")
        if not self.source.is_dir():
            raise OrganizationError(f"A origem não é uma pasta: {self.source}")
        if self.source.is_symlink():
            raise OrganizationError("A pasta de origem não pode ser um link simbólico.")

        for source_path in self._iter_files(summary):
            category = self._category_for(source_path)
            target_dir = source_path.parent / category
            desired_target = target_dir / source_path.name
            try:
                target = desired_target
                if target.exists():
                    if self.config.conflict_strategy == "skip":
                        summary.skipped += 1
                        summary.operations.append(FileOperation(str(source_path), str(target), "skipped", "conflito"))
                        self._log(20, f"Conflito; ignorado: {source_path}")
                        continue
                    if self.config.conflict_strategy == "rename":
                        target = self._available_target(desired_target)

                summary.planned += 1
                if self.dry_run:
                    summary.operations.append(FileOperation(str(source_path), str(target), "planned"))
                    self._log(20, f"Simulação: {source_path} -> {target}")
                    continue

                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target))
                summary.moved += 1
                summary.operations.append(FileOperation(str(source_path), str(target), "moved"))
                self._log(20, f"Movido: {source_path} -> {target}")
            except (OSError, shutil.Error) as exc:
                self._record_error(summary, f"Falha ao organizar {source_path}: {exc}")
                summary.operations.append(FileOperation(str(source_path), str(desired_target), "error", str(exc)))
        return summary
