"""Modelos e validação da configuração JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


class ConfigError(ValueError):
    """Erro de sintaxe ou de validação da configuração."""


def _normalise_extension(value: Any, *, category: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"A extensão da categoria '{category}' deve ser texto não vazio.")
    extension = value.strip().lower()
    if not extension.startswith("."):
        extension = "." + extension
    if extension == "." or any(char in extension for char in ("/", "\\", "\n", "\r")):
        raise ConfigError(f"Extensão inválida na categoria '{category}': {value!r}.")
    return extension


def _validate_category_name(name: Any) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ConfigError("Os nomes de categoria devem ser textos não vazios.")
    clean = name.strip()
    if clean in {".", ".."} or any(char in clean for char in ("/", "\\", "\x00", "\n", "\r")):
        raise ConfigError(f"Nome de categoria inválido: {name!r}.")
    return clean


def default_categories() -> dict[str, list[str]]:
    """Retorna uma cópia das categorias padrão (sem estado global mutável)."""
    return {
        "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tif", ".tiff"],
        "Documentos": [".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".md"],
        "Planilhas": [".xls", ".xlsx", ".ods", ".csv", ".tsv"],
        "Apresentacoes": [".ppt", ".pptx", ".odp"],
        "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"],
        "Audios": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"],
        "Compactados": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
        "Codigo": [
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs",
            ".rb", ".php", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sql", ".sh",
        ],
    }


@dataclass(slots=True)
class OrganizerConfig:
    """Configuração validada usada por :class:`FileOrganizer`."""

    categories: dict[str, list[str]] = field(default_factory=default_categories)
    unknown_category: str = "Outros"
    recursive: bool = False
    include_hidden: bool = False
    conflict_strategy: str = "rename"
    ignore: list[str] = field(default_factory=lambda: [".git"])

    def __post_init__(self) -> None:
        raw_categories = self.categories
        if not isinstance(raw_categories, dict) or not raw_categories:
            raise ConfigError("'categories' deve ser um objeto JSON não vazio.")

        normalised: dict[str, list[str]] = {}
        extensions_seen: dict[str, str] = {}
        for raw_name, raw_extensions in raw_categories.items():
            name = _validate_category_name(raw_name)
            if not isinstance(raw_extensions, list) or not raw_extensions:
                raise ConfigError(f"A categoria '{name}' deve conter uma lista não vazia de extensões.")
            extensions: list[str] = []
            for raw_extension in raw_extensions:
                extension = _normalise_extension(raw_extension, category=name)
                previous = extensions_seen.get(extension)
                if previous is not None and previous != name:
                    raise ConfigError(
                        f"A extensão '{extension}' aparece nas categorias '{previous}' e '{name}'."
                    )
                extensions_seen[extension] = name
                if extension not in extensions:
                    extensions.append(extension)
            normalised[name] = extensions

        self.categories = normalised
        self.unknown_category = _validate_category_name(self.unknown_category)
        if self.unknown_category in self.categories:
            raise ConfigError("'unknown_category' não pode coincidir com uma categoria configurada.")
        if not isinstance(self.recursive, bool):
            raise ConfigError("'recursive' deve ser booleano.")
        if not isinstance(self.include_hidden, bool):
            raise ConfigError("'include_hidden' deve ser booleano.")
        if self.conflict_strategy not in {"rename", "skip", "overwrite"}:
            raise ConfigError("'conflict_strategy' deve ser 'rename', 'skip' ou 'overwrite'.")
        if not isinstance(self.ignore, list) or any(not isinstance(item, str) or not item for item in self.ignore):
            raise ConfigError("'ignore' deve ser uma lista de nomes de arquivo/pasta não vazios.")
        self.ignore = list(dict.fromkeys(self.ignore))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "OrganizerConfig":
        if not isinstance(data, Mapping):
            raise ConfigError("A configuração JSON deve ser um objeto.")
        allowed = {"categories", "unknown_category", "recursive", "include_hidden", "conflict_strategy", "ignore"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ConfigError(f"Chaves de configuração desconhecidas: {', '.join(unknown)}.")
        values = dict(data)
        if "categories" not in values:
            values["categories"] = default_categories()
        return cls(**values)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "categories": {key: list(values) for key, values in self.categories.items()},
            "unknown_category": self.unknown_category,
            "recursive": self.recursive,
            "include_hidden": self.include_hidden,
            "conflict_strategy": self.conflict_strategy,
            "ignore": list(self.ignore),
        }


def load_config(path: str | Path | None) -> OrganizerConfig:
    """Carrega uma configuração JSON; ``None`` significa usar os padrões."""
    if path is None:
        return OrganizerConfig()
    config_path = Path(path)
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Arquivo de configuração não encontrado: {config_path}") from exc
    except PermissionError as exc:
        raise ConfigError(f"Sem permissão para ler a configuração: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON inválido em {config_path}: linha {exc.lineno}, coluna {exc.colno}.") from exc
    except OSError as exc:
        raise ConfigError(f"Não foi possível ler a configuração {config_path}: {exc}") from exc
    return OrganizerConfig.from_mapping(data)
