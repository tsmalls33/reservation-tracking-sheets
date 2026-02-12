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

# Month name translations
MONTH_NAMES = {
    'january': {'en': 'January', 'es': 'Enero'},
    'february': {'en': 'February', 'es': 'Febrero'},
    'march': {'en': 'March', 'es': 'Marzo'},
    'april': {'en': 'April', 'es': 'Abril'},
    'may': {'en': 'May', 'es': 'Mayo'},
    'june': {'en': 'June', 'es': 'Junio'},
    'july': {'en': 'July', 'es': 'Julio'},
    'august': {'en': 'August', 'es': 'Agosto'},
    'september': {'en': 'September', 'es': 'Septiembre'},
    'october': {'en': 'October', 'es': 'Octubre'},
    'november': {'en': 'November', 'es': 'Noviembre'},
    'december': {'en': 'December', 'es': 'Diciembre'}
}

# Month abbreviations and groups
MONTH_ABBREV = {
    'jan': 'january', 'feb': 'february', 'mar': 'march',
    'apr': 'april', 'may': 'may', 'jun': 'june',
    'jul': 'july', 'aug': 'august', 'sep': 'september',
    'oct': 'october', 'nov': 'november', 'dec': 'december'
}

MONTH_GROUPS = {
    'q1': ['jan', 'feb', 'mar'],
    'q2': ['apr', 'may', 'jun'],
    'q3': ['jul', 'aug', 'sep'],
    'q4': ['oct', 'nov', 'dec'],
    'all': ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
            'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
}


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


def parse_months(month_input):
    """Parse month input (jan,feb,q1,all) into list of month keys.
    
    Args:
        month_input: Comma-separated string like 'jan,feb' or 'q1' or 'all'
    
    Returns:
        List of month keys: ['january', 'february', ...]
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


def translate_tab_names(config_data, target_language):
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
    • Invoice generation from reservation data
    
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
    delete configs, and manage spreadsheet settings.
    """
    pass


@cli.group()
def invoice():
    """Manage invoices.
    
    Create invoices from reservation data, list existing invoices,
    and manage invoice templates.
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
    4. Setting language (EN/ES) - automatically translates tab names
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
    
    # Translate tab names if language changed
    if new_language.lower() != current_lang.lower():
        click.echo(f"\n🔄 Translating tab names from {current_lang.upper()} to {new_language.upper()}...")
        new_config = translate_tab_names(new_config, new_language.lower())
        click.echo(click.style("   ✓ Tab names translated", fg="green"))
    
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
    click.echo(f"\n💡 {click.style('Remember:', fg='yellow', bold=True)} Share the Google Sheet with your service account email")
    click.echo(f"   (found in credentials/service_account.json or in notes.md) as {click.style('Editor', bold=True)}")
    click.echo(f"\nUse with: {click.style(f'reservations upload file.csv -a {apartment_name} -y {year}', fg='cyan')}")
    click.echo()


@config.command('delete')
def config_delete():
    """Delete one or more configuration files.
    
    Displays a numbered list of all configs and allows deletion
    of single or multiple configs (e.g., 1 or 1,3,5).
    """
    configs = list_config_files()
    
    if not configs:
        click.echo(click.style("❌ No configuration files found in config/", fg="red"))
        return
    
    # Build flat list of all configs
    all_configs = []
    for apartment in sorted(configs.keys()):
        for config_file in sorted(configs[apartment]):
            all_configs.append(config_file)
    
    # Show available configs
    click.echo("\n" + "="*70)
    click.echo(click.style("  DELETE CONFIGURATION FILES", bold=True))
    click.echo("="*70)
    click.echo("\n🗑️  Available configs:\n")
    
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
    
    # Get user selection
    click.echo()
    click.echo("Enter config number(s) to delete:")
    click.echo("  Single: 3")
    click.echo("  Multiple: 1,4,5")
    
    selection = click.prompt('\nSelection', type=str)
    
    # Parse selection
    try:
        indices = [int(x.strip()) for x in selection.split(',')]
    except ValueError:
        click.echo(click.style("❌ Invalid input. Use numbers separated by commas.", fg="red"))
        return
    
    # Validate indices
    invalid = [i for i in indices if i < 1 or i > len(all_configs)]
    if invalid:
        click.echo(click.style(f"❌ Invalid selection(s): {', '.join(map(str, invalid))}", fg="red"))
        return
    
    # Get files to delete
    files_to_delete = [all_configs[i - 1] for i in indices]
    
    # Show confirmation
    click.echo("\n" + "-"*70)
    click.echo("Files to be deleted:\n")
    for f in files_to_delete:
        click.echo(f"  ❌ {click.style(f.name, fg='red')}")
    
    click.echo()
    if not click.confirm(click.style('Are you sure? This cannot be undone!', fg='red', bold=True), default=False):
        click.echo(click.style("❌ Cancelled", fg="yellow"))
        return
    
    # Delete files
    deleted_count = 0
    for config_file in files_to_delete:
        try:
            config_file.unlink()
            click.echo(f"✅ Deleted: {config_file.name}")
            deleted_count += 1
        except Exception as e:
            click.echo(click.style(f"❌ Failed to delete {config_file.name}: {e}", fg="red"))
    
    click.echo("\n" + "="*70)
    click.echo(click.style(f"  ✅ DELETED {deleted_count} CONFIG(S)", fg="green", bold=True))
    click.echo("="*70)
    click.echo()


@invoice.command('create')
@click.option('--apartment', '-a', required=True, help='Apartment name')
@click.option('--months', '-m', required=True, 
              help='Months (jan,feb or q1,q2 or all)')
@click.option('--year', '-y', type=int, default=2026, help='Year (default: 2026)')
@click.option('--email', '-e', help='Email to share invoice with')
@click.option('--test', is_flag=True,
              help='Use test reservation config and TEST_ invoice numbering')
def invoice_create(apartment, months, year, email, test):
    """Create an invoice from reservation data.
    
    Extracts financial data from specified months and generates
    a new invoice by copying the template and populating it with
    aggregated data.
    
    \b
    Month Options:
      Individual: jan,feb,mar
      Quarters: q1 (jan-mar), q2 (apr-jun), q3 (jul-sep), q4 (oct-dec)
      Full year: all
    
    \b
    Examples:
      # Production invoice
      reservations invoice create -a mediona -m jan -y 2025
      
      # Test invoice (uses test config, TEST_ numbering)
      reservations invoice create -a mediona -m jan -y 2025 --test
      
      # Multiple months
      reservations invoice create -a mediona -m jan,feb,mar -y 2025
      
      # Quarter
      reservations invoice create -a mediona -m q1 -y 2025
      
      # Full year
      reservations invoice create -a mediona -m all -y 2025
      
      # With email sharing
      reservations invoice create -a mediona -m q1 -y 2025 -e your@email.com
    """
    try:
        # Parse months
        month_list = parse_months(months)
        
        mode_label = click.style('[TEST]', fg='yellow') if test else click.style('[PROD]', fg='green')
        click.echo(f"\n{mode_label} Creating invoice...")
        click.echo(f"📅 Months: {', '.join([m.capitalize() for m in month_list])}")
        
        # Call invoice creation script
        invoice_script = PROJECT_ROOT / "scripts/create_invoice.py"
        cmd = [
            sys.executable, str(invoice_script),
            '--apartment', apartment,
            '--months', ','.join(month_list),
            '--year', str(year)
        ]
        
        if test:
            cmd.append('--test')
        
        if email:
            cmd.extend(['--email', email])
        
        subprocess.run(cmd, check=True)
        
    except ValueError as e:
        click.echo(click.style(f"❌ {e}", fg="red"))
        sys.exit(1)
    except subprocess.CalledProcessError:
        click.echo(click.style("❌ Invoice creation failed!", fg="red"))
        sys.exit(1)


@invoice.command('list')
@click.option('--apartment', '-a', help='Filter by apartment')
def invoice_list(apartment):
    """List all generated invoices.
    
    Shows invoice numbers, dates, months covered, and spreadsheet links.
    Optionally filter by apartment.
    """
    invoices_dir = PROJECT_ROOT / "invoices"
    
    if not invoices_dir.exists():
        click.echo(click.style("❌ No invoices directory found", fg="red"))
        return
    
    # Collect all invoices
    all_invoices = []
    
    if apartment:
        # Filter by apartment
        apartment_dir = invoices_dir / apartment
        if apartment_dir.exists():
            for invoice_file in apartment_dir.glob('*.json'):
                try:
                    with open(invoice_file, 'r') as f:
                        data = json.load(f)
                        data['apartment'] = apartment
                        all_invoices.append(data)
                except:
                    pass
    else:
        # All apartments
        for apartment_dir in invoices_dir.iterdir():
            if apartment_dir.is_dir():
                for invoice_file in apartment_dir.glob('*.json'):
                    try:
                        with open(invoice_file, 'r') as f:
                            data = json.load(f)
                            all_invoices.append(data)
                    except:
                        pass
    
    if not all_invoices:
        click.echo(click.style("❌ No invoices found", fg="yellow"))
        click.echo(f"\nCreate one with: {click.style('reservations invoice create -a mediona -m jan', fg='cyan')}")
        return
    
    # Sort by created date
    all_invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Display
    click.echo("\n" + "="*70)
    click.echo(click.style("  INVOICES", bold=True))
    click.echo("="*70)
    
    for inv in all_invoices:
        is_test = inv.get('test_mode', False)
        badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')
        
        click.echo(f"\n{badge} {click.style(inv['invoice_number'], fg='cyan', bold=True)}")
        click.echo(f"   Apartment: {inv['apartment']}")
        click.echo(f"   Months: {', '.join([m.capitalize() for m in inv['months']])}")
        click.echo(f"   Year: {inv['year']}")
        click.echo(f"   Created: {inv['created_at'][:10]}")
        click.echo(f"   🔗 {inv.get('sheet_url', 'N/A')}")
    
    click.echo(f"\n📊 Total: {len(all_invoices)} invoice(s)")
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
