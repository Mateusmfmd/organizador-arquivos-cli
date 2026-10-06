"""Organizador de arquivos por extensão/categoria."""

__version__ = "1.0.0"

from .config import OrganizerConfig, ConfigError, load_config
from .organizer import FileOrganizer, OrganizationError, OrganizationSummary

__all__ = [
    "__version__",
    "OrganizerConfig",
    "ConfigError",
    "load_config",
    "FileOrganizer",
    "OrganizationError",
    "OrganizationSummary",
]
