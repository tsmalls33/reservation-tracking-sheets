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
