"""Utility functions for the CLI."""

from .config import list_config_files
from .platform import detect_platform
from .months import parse_months, translate_tab_names
from .completion import complete_apartment, complete_months, complete_year
from .display import success, error, info, warning, section_header

__all__ = [
    'list_config_files',
    'detect_platform',
    'parse_months',
    'translate_tab_names',
    'complete_apartment',
    'complete_months',
    'complete_year',
    'success',
    'error',
    'info',
    'warning',
    'section_header',
]
