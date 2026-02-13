"""Month parsing and translation utilities."""

from ..constants import MONTH_NAMES, MONTH_ABBREV, MONTH_GROUPS


def parse_months(month_input: str) -> list:
    """Parse month input (jan,feb,q1,all) into list of month keys.
    
    Args:
        month_input: Comma-separated string like 'jan,feb' or 'q1' or 'all'
    
    Returns:
        List of month keys: ['january', 'february', ...]
        
    Raises:
        ValueError: If invalid month input
    """
    parts = [m.strip().lower() for m in month_input.split(',')]
    abbrevs = []
    
    for part in parts:
        if part in MONTH_GROUPS:
            # Expand group (q1, q2, etc.)
            abbrevs.extend(MONTH_GROUPS[part])
        elif part in MONTH_ABBREV:
            # Individual month
            abbrevs.append(part)
        else:
            raise ValueError(
                f"Invalid month: '{part}'.\n"
                f"Valid options: jan-dec, q1-q4, all"
            )
    
    # Convert abbreviations to full month names
    return [MONTH_ABBREV[a] for a in abbrevs]


def translate_tab_names(config_data: dict, target_language: str) -> dict:
    """Translate all tab_name values in config to target language.
    
    Args:
        config_data: Config dictionary
        target_language: 'en' or 'es'
    
    Returns:
        Updated config_data with translated tab names
    """
    if 'tabs' not in config_data:
        return config_data
    
    # Build reverse lookup: month name -> month key
    month_lookup = {}
    for month_key, translations in MONTH_NAMES.items():
        month_lookup[translations['en'].lower()] = month_key
        month_lookup[translations['es'].lower()] = month_key
    
    # Update each tab's tab_name
    for tab_key, tab_config in config_data['tabs'].items():
        if 'tab_name' not in tab_config:
            continue
        
        current_tab_name = tab_config['tab_name'].strip()
        
        # Find the month key from current tab name
        month_key = month_lookup.get(current_tab_name.lower())
        
        if month_key:
            # Translate to target language
            new_tab_name = MONTH_NAMES[month_key][target_language]
            tab_config['tab_name'] = new_tab_name
    
    return config_data
