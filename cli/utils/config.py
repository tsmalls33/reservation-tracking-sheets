"""Configuration file utilities."""

from pathlib import Path
from collections import defaultdict


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
