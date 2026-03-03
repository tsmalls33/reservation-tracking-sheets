"""Shell tab-completion callbacks for CLI options."""

from click.shell_completion import CompletionItem


def complete_apartment(ctx, param, incomplete):
    """Complete apartment names from config filenames."""
    try:
        from .. import CONFIG_DIR
        from .config import list_config_files

        configs = list_config_files(CONFIG_DIR)
        return [
            CompletionItem(name)
            for name in sorted(configs.keys())
            if name.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_year(ctx, param, incomplete):
    """Complete years from config filenames."""
    try:
        from .. import CONFIG_DIR

        if not CONFIG_DIR.exists():
            return []

        years = set()
        for config_file in CONFIG_DIR.glob('*.json'):
            if config_file.name == 'invoices.json':
                continue
            parts = config_file.stem.split('_')
            for part in reversed(parts):
                if part.isdigit() and len(part) == 4:
                    years.add(part)
                    break

        incomplete_str = str(incomplete)
        return [
            CompletionItem(y)
            for y in sorted(years)
            if y.startswith(incomplete_str)
        ]
    except Exception:
        return []


def complete_months(ctx, param, incomplete):
    """Complete month abbreviations, quarters, and 'all'.

    Handles comma-separated input by completing only the segment
    after the last comma. Already-selected values are excluded.
    """
    try:
        from ..constants import MONTH_ABBREV, MONTH_GROUPS

        all_options = list(MONTH_ABBREV.keys()) + list(MONTH_GROUPS.keys())

        # Handle comma-separated: complete only the last segment
        if ',' in incomplete:
            prefix, _, current = incomplete.rpartition(',')
            prefix = prefix + ','
        else:
            prefix = ''
            current = incomplete

        # Exclude already-selected values
        already_selected = set()
        if prefix:
            already_selected = {
                p.strip().lower()
                for p in prefix.rstrip(',').split(',')
            }

        return [
            CompletionItem(prefix + option)
            for option in sorted(all_options)
            if option.startswith(current.lower())
            and option not in already_selected
        ]
    except Exception:
        return []
