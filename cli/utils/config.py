"""Configuration file utilities."""

import json
from pathlib import Path
from collections import defaultdict

import click


def list_config_files(config_dir: Path) -> dict:
    """Get all config files organized by apartment.

    Args:
        config_dir: Path to config directory

    Returns:
        dict: {apartment_name: [config_files]}
    """
    if not config_dir.exists():
        return {}

    configs = defaultdict(list)
    for config_file in config_dir.glob('*.json'):
        # Skip invoices config
        if config_file.name == 'invoices.json':
            continue

        # Parse filename: apartment_year[_test].json
        name = config_file.stem
        parts = name.split('_')

        if len(parts) >= 2:
            # Extract apartment name (everything except last part which is year[_test])
            year_part = parts[-1]
            if year_part == 'test':
                # apartment_year_test format
                apartment = '_'.join(parts[:-2])
            else:
                # apartment_year format
                apartment = '_'.join(parts[:-1])

            configs[apartment].append(config_file)

    return dict(configs)


def get_flat_config_list(config_dir: Path) -> list:
    """Get a flat, sorted list of all config file paths.

    Flattens the grouped dict from list_config_files into a single list,
    sorted by apartment name then file name.

    Args:
        config_dir: Path to config directory

    Returns:
        list: Sorted list of Path objects for all config files
    """
    configs = list_config_files(config_dir)
    all_configs = []
    for apartment in sorted(configs.keys()):
        for config_file in sorted(configs[apartment]):
            all_configs.append(config_file)
    return all_configs


def display_numbered_config_list(config_files: list) -> None:
    """Display a numbered list of config files with TEST/PROD and language badges.

    Each entry shows:
      1. [TEST] [EN] apartment_2026_test.json
      2. [PROD] [ES] apartment_2026.json

    Args:
        config_files: List of Path objects for config files
    """
    for idx, config_file in enumerate(config_files, 1):
        name = config_file.stem
        is_test = name.endswith('_test')
        badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                language = data.get('language', 'en').upper()
                lang_badge = click.style(f'[{language}]', fg='blue')
                click.echo(f"  {idx}. {badge} {lang_badge} {config_file.name}")
        except Exception:
            click.echo(f"  {idx}. {config_file.name}")


def validate_apartment_config(config_dir: Path, apartment: str, year: int, test: bool = False) -> Path:
    """Validate that an apartment config file exists.

    Args:
        config_dir: Path to config directory
        apartment: Apartment name
        year: Year
        test: Whether to use test config

    Returns:
        Path to the config file

    Raises:
        click.BadParameter: If config file not found, listing available apartments
    """
    suffix = '_test' if test else ''
    config_file = config_dir / f"{apartment}_{year}{suffix}.json"

    if config_file.exists():
        return config_file

    # Config not found — list available apartments
    available = list_config_files(config_dir)
    if available:
        names = ', '.join(sorted(available.keys()))
        raise click.BadParameter(
            f"Config not found: {apartment}_{year}{suffix}.json\n"
            f"  Available apartments: {names}"
        )
    else:
        raise click.BadParameter(
            f"Config not found: {apartment}_{year}{suffix}.json\n"
            f"  No config files found in {config_dir}/"
        )


def validate_config_structure(config_data: dict, config_path: Path) -> None:
    """Validate that a config has the required keys.

    Args:
        config_data: Parsed config dictionary
        config_path: Path to config file (for error messages)

    Raises:
        click.BadParameter: If required keys are missing
    """
    required_keys = ['spreadsheet_id', 'tabs']
    missing = [k for k in required_keys if k not in config_data]

    if missing:
        raise click.BadParameter(
            f"Invalid config {config_path.name}: missing required key(s): {', '.join(missing)}"
        )


def load_and_validate_config(config_dir: Path, apartment: str, year: int, test: bool = False) -> dict:
    """Validate apartment config exists, load it, and validate its structure.

    Args:
        config_dir: Path to config directory
        apartment: Apartment name
        year: Year
        test: Whether to use test config

    Returns:
        Parsed and validated config dictionary

    Raises:
        click.BadParameter: If config not found or invalid
    """
    config_path = validate_apartment_config(config_dir, apartment, year, test)

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    validate_config_structure(config_data, config_path)
    return config_data
