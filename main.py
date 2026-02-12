#!/usr/bin/env python3
"""
Reservations CLI - Process and upload Airbnb/Booking data to Google Sheets

Supports multiple CSV files from Airbnb and Booking.com, automatically
detects platforms, processes data, and uploads to configured Google Sheets
with dynamic column mapping.
"""

import warnings
import os

# Suppress all warnings at startup
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import click
import subprocess
import sys
import json
import shutil
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")
CONFIG_DIR = PROJECT_ROOT / "config"


def detect_platform(filename):
    """Automatically detect if a CSV is from Airbnb or Booking.com.
    
    Args:
        filename: Path to CSV file
        
    Returns:
        'airbnb' or 'booking'
        
    Raises:
        ValueError: If platform cannot be detected
    """
    fn_lower = Path(filename).name.lower()
    
    # Check filename patterns
    if any(x in fn_lower for x in ['airbnb', 'confirmación', 'hm']):
        return 'airbnb'
    if any(x in fn_lower for x in ['booking', 'reservation', 'invoice']):
        return 'booking'
    
    # Quick content check if filename doesn't match
    try:
        content = Path(filename).read_text(errors='ignore')[:1000].lower()
        if any(x in content for x in ['airbnb', 'confirmación', 'hm']):
            return 'airbnb'
        if any(x in content for x in ['booking', 'reservation number', 'invoice number']):
            return 'booking'
    except:
        pass
    
    raise ValueError(
        f"Cannot detect platform for: {filename}\n"
        f"Expected 'airbnb' or 'booking' in filename or content."
    )


def list_config_files():
    """Get all config files organized by apartment.
    
    Returns:
        dict: {apartment_name: [config_files]}
    """
    if not CONFIG_DIR.exists():
        return {}
    
    configs = defaultdict(list)
    for config_file in CONFIG_DIR.glob('*.json'):
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


@click.group()
@click.version_option("2.0.0")
def cli():
    """Reservation Tracking System - Automate Airbnb/Booking data to Google Sheets.
    
    This tool processes reservation CSVs from Airbnb and Booking.com, then uploads
    them to Google Sheets with dynamic column mapping based on your configuration.
    
    \b
    Features:
    • Auto-detects platform (Airbnb/Booking.com)
    • Processes multiple CSVs in one command
    • Dynamic column mapping per apartment
    • Spanish/English month name support
    • Calculated fields (e.g., sum of Precio + Comision)
    • Smart clearing (only detected months) or hard replace (all months)
    
    \b
    Example:
      reservations upload airbnb_jan.csv booking_feb.csv -a mediona -y 2026
    
    \b
    Configuration:
      Configs are stored in config/{apartment}_{year}.json
      Each config defines spreadsheet ID, tab names, columns, and mappings.
    """
    pass


@cli.group()
def config():
    """Manage configuration files for apartments.
    
    Create new configs from templates, list existing configs,
    and manage spreadsheet settings.
    """
    pass


@config.command('list')
def config_list():
    """List all available configuration files grouped by apartment.
    
    Shows all config files organized by apartment name, including
    year and test/production variants.
    """
    configs = list_config_files()
    
    if not configs:
        click.echo(click.style("❌ No configuration files found in config/", fg="red"))
        click.echo(f"\nCreate a config with: {click.style('reservations config create', fg='cyan')}")
        return
    
    click.echo("\n" + "="*70)
    click.echo(click.style("  CONFIGURATION FILES", bold=True))
    click.echo("="*70)
    
    for apartment in sorted(configs.keys()):
        click.echo(f"\n🏠 {click.style(apartment, fg='cyan', bold=True)}")
        
        for config_file in sorted(configs[apartment]):
            # Parse config details
            name = config_file.stem
            is_test = name.endswith('_test')
            
            # Try to read language and spreadsheet ID
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    sheet_id = data.get('spreadsheet_id', 'N/A')[:30]
                    language = data.get('language', 'en').upper()
                    
                    badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')
                    lang_badge = click.style(f'[{language}]', fg='blue')
                    
                    click.echo(f"  {badge} {lang_badge} {config_file.name}")
                    click.echo(f"     → Sheet: {sheet_id}...")
            except:
                click.echo(f"  ⚠️  {config_file.name} (invalid JSON)")
    
    click.echo(f"\n📊 Total: {sum(len(v) for v in configs.values())} config(s) across {len(configs)} apartment(s)")
    click.echo()


@config.command('create')
def config_create():
    """Create a new configuration file from an existing template.
    
    Interactively guides you through:
    1. Choosing a template config to clone
    2. Setting apartment name and year
    3. Configuring Google Sheet ID
    4. Setting language (EN/ES)
    """
    configs = list_config_files()
    
    if not configs:
        click.echo(click.style("❌ No existing configs to use as template!", fg="red"))
        click.echo("\nCreate your first config manually in config/ directory.")
        return
    
    # Show available templates
    click.echo("\n" + "="*70)
    click.echo(click.style("  CREATE NEW CONFIG", bold=True))
    click.echo("="*70)
    click.echo("\n📋 Available templates:\n")
    
    all_configs = []
    for apartment in sorted(configs.keys()):
        for config_file in sorted(configs[apartment]):
            all_configs.append(config_file)
    
    for idx, config_file in enumerate(all_configs, 1):
        name = config_file.stem
        is_test = name.endswith('_test')
        badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                language = data.get('language', 'en').upper()
                lang_badge = click.style(f'[{language}]', fg='blue')
                click.echo(f"  {idx}. {badge} {lang_badge} {config_file.name}")
        except:
            click.echo(f"  {idx}. {config_file.name}")
    
    # Get user choice
    click.echo()
    choice = click.prompt('Choose a template (number)', type=int)
    
    if choice < 1 or choice > len(all_configs):
        click.echo(click.style("❌ Invalid choice", fg="red"))
        return
    
    template_file = all_configs[choice - 1]
    click.echo(f"\n✅ Using template: {click.style(template_file.name, fg='cyan')}")
    
    # Load template
    with open(template_file, 'r') as f:
        template_data = json.load(f)
    
    # Get new config details
    click.echo("\n" + "-"*70)
    click.echo("Enter details for new configuration:\n")
    
    apartment_name = click.prompt('Apartment name (e.g., mediona, sant-domenec)', type=str)
    year = click.prompt('Year', type=int, default=2026)
    is_test = click.confirm('Create as test config?', default=False)
    
    # Get Google Sheet ID
    click.echo(f"\n📋 Current sheet ID: {template_data.get('spreadsheet_id', 'N/A')}")
    new_sheet_id = click.prompt('New Google Sheet ID', type=str)
    
    # Get language if config supports it
    current_lang = template_data.get('language', 'en')
    click.echo(f"\n🌍 Current language: {current_lang.upper()}")
    new_language = click.prompt('Language (en/es)', type=click.Choice(['en', 'es'], case_sensitive=False), default=current_lang)
    
    # Build new config
    new_config = template_data.copy()
    new_config['spreadsheet_id'] = new_sheet_id
    new_config['language'] = new_language.lower()
    
    # Generate filename
    suffix = '_test' if is_test else ''
    new_filename = f"{apartment_name}_{year}{suffix}.json"
    new_filepath = CONFIG_DIR / new_filename
    
    # Check if file exists
    if new_filepath.exists():
        click.echo(f"\n⚠️  {new_filename} already exists!")
        if not click.confirm('Overwrite?', default=False):
            click.echo(click.style("❌ Cancelled", fg="red"))
            return
    
    # Save new config
    with open(new_filepath, 'w') as f:
        json.dump(new_config, f, indent=2)
    
    click.echo("\n" + "="*70)
    click.echo(click.style("  ✅ CONFIG CREATED", fg="green", bold=True))
    click.echo("="*70)
    click.echo(f"File: {click.style(new_filename, fg='cyan')}")
    click.echo(f"Path: {new_filepath}")
    click.echo(f"Sheet ID: {new_sheet_id}")
    click.echo(f"Language: {new_language.upper()}")
    click.echo(f"Type: {'Test' if is_test else 'Production'}")
    click.echo(f"\nUse with: {click.style(f'reservations upload file.csv -a {apartment_name} -y {year}', fg='cyan')}")
    click.echo()


@cli.command()
@click.argument('csv_files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--apartment', '-a', required=True, 
              help='Apartment name (matches config file: {apartment}_{year}.json)')
@click.option('--year', '-y', type=int, default=2026,
              help='Year for config file (default: 2026)')
@click.option('--test', is_flag=True,
              help='Use test configuration ({apartment}_{year}_test.json)')
@click.option('--hard-replace', '-H', is_flag=True,
              help='Clear ALL month tabs (default: only clear detected months)')
def upload(csv_files, apartment, year, test, hard_replace):
    """Process and upload reservation CSVs to Google Sheets.
    
    Automatically detects platform (Airbnb/Booking.com), processes CSVs,
    merges if multiple files provided, and uploads to the configured
    Google Sheet.
    
    \b
    CSV_FILES: One or more CSV files from Airbnb or Booking.com
    
    \b
    Examples:
      # Upload single file
      reservations upload airbnb_export.csv -a mediona -y 2026
      
      # Upload multiple files (auto-merges)
      reservations upload airbnb.csv booking.csv -a sant-domenec -y 2026
      
      # Use test config
      reservations upload data.csv -a mediona -y 2026 --test
      
      # Clear all months before upload
      reservations upload data.csv -a mediona -y 2026 --hard-replace
    
    \b
    What happens:
      1. Auto-detects platform for each CSV
      2. Processes each file (standardizes format)
      3. Merges if multiple CSVs provided
      4. Uploads to Google Sheets using config/{apartment}_{year}.json
      5. Smart clearing: only clears months found in CSVs (unless --hard-replace)
    
    \b
    Configuration:
      Creates/updates config at: config/{apartment}_{year}.json
      Config defines: spreadsheet ID, tab names, columns, language, mappings
    
    \b
    Notes:
      • Preserves sheet formatting and data validation
      • Writes month names to cell B2 in configured language
      • Supports calculated fields (e.g., Precio Total = Precio + Comision)
      • Handles merged cells (F/G columns)
    """
    
    if not csv_files:
        click.echo(click.style("❌ Error: Provide at least one CSV file", fg="red"))
        sys.exit(1)
    
    # Create temp directory
    temp_dir = PROJECT_ROOT / "data" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each CSV
    processed_files = []
    click.echo("\n" + "="*70)
    click.echo(click.style("  PROCESSING CSVs", bold=True))
    click.echo("="*70)
    
    for csv_file in csv_files:
        try:
            platform = detect_platform(csv_file)
            script_path = PROJECT_ROOT / f"scripts/process_{platform}.py"
            processed = temp_dir / f"{Path(csv_file).stem}_{platform}_processed.csv"
            
            click.echo(f"\n🔄 Processing {click.style(platform.upper(), fg='cyan')}: {Path(csv_file).name}")
            
            # Process with real-time output
            subprocess.run([
                sys.executable, str(script_path), 
                str(csv_file), str(processed)
            ], check=True)
            
            processed_files.append(processed)
            click.echo(click.style(f"   ✓ Processed", fg="green"))
            
        except ValueError as e:
            click.echo(click.style(f"\n❌ {e}", fg="red"))
            sys.exit(1)
        except subprocess.CalledProcessError:
            click.echo(click.style(f"\n❌ Processing failed for {csv_file}", fg="red"))
            sys.exit(1)
    
    # Merge if multiple files
    if len(processed_files) > 1:
        click.echo("\n" + "-"*70)
        merge_script = PROJECT_ROOT / "scripts/merge_data.py"
        merged = temp_dir / f"{apartment}_{year}_merged.csv"
        
        click.echo(f"🔀 Merging {click.style(str(len(processed_files)), fg='cyan')} files...")
        subprocess.run([
            sys.executable, str(merge_script),
            *[str(f) for f in processed_files], str(merged)
        ], check=True)
        final_csv = merged
        click.echo(click.style("   ✓ Merged", fg="green"))
    else:
        final_csv = processed_files[0]
    
    # Upload
    click.echo("\n" + "="*70)
    click.echo(click.style("  UPLOADING TO GOOGLE SHEETS", bold=True))
    click.echo("="*70)
    
    upload_script = PROJECT_ROOT / "scripts/upload_to_sheets.py"
    cmd = [
        sys.executable, str(upload_script),
        '--csv', str(final_csv),
        '--apartment', apartment,
        '--year', str(year)
    ]
    if test:
        cmd.append('--test')
    if hard_replace:
        cmd.append('--hard-replace')

    config_suffix = '_test' if test else ''
    click.echo(f"📤 Target: {click.style(f'{apartment}_{year}{config_suffix}', fg='cyan')}")
    
    try:
        # Upload with real-time output
        subprocess.run(cmd, check=True)
        
        click.echo("\n" + "="*70)
        click.echo(click.style("  ✅ SUCCESS", fg="green", bold=True))
        click.echo("="*70)
        click.echo(f"Uploaded to: {apartment}_{year}{config_suffix}")
        click.echo()
        
    except subprocess.CalledProcessError:
        click.echo("\n" + "="*70)
        click.echo(click.style("  ❌ UPLOAD FAILED", fg="red", bold=True))
        click.echo("="*70)
        sys.exit(1)


if __name__ == '__main__':
    cli()
