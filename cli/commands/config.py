"""Configuration management commands."""

import sys
import json
import click
from .. import CONFIG_DIR
from ..utils.config import list_config_files, get_flat_config_list, display_numbered_config_list
from ..utils.months import translate_tab_names
from ..utils.display import error, success, warning, section_header


@click.group()
def config():
    """Manage configuration files for apartments.
    
    Create new configs from templates, list existing configs,
    delete configs, and manage spreadsheet settings.
    """
    pass


@config.command('list')
def config_list():
    """List all available configuration files grouped by apartment.
    
    Shows all config files organized by apartment name, including
    year and test/production variants.
    """
    configs = list_config_files(CONFIG_DIR)
    
    if not configs:
        error("No configuration files found in config/")
        click.echo(f"\nCreate a config with: {click.style('reservations config create', fg='cyan')}")
        sys.exit(1)

    section_header("CONFIGURATION FILES")
    
    for apartment in sorted(configs.keys()):
        click.echo(f"\n🏠 {click.style(apartment, fg='cyan', bold=True)}")
        
        for config_file in sorted(configs[apartment]):
            # Parse config details
            name = config_file.stem
            is_test = name.endswith('_test')
            
            # Try to read language and spreadsheet ID
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sheet_id = data.get('spreadsheet_id', 'N/A')[:30]
                    language = data.get('language', 'en').upper()

                    badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')
                    lang_badge = click.style(f'[{language}]', fg='blue')

                    click.echo(f"  {badge} {lang_badge} {config_file.name}")
                    click.echo(f"     → Sheet: {sheet_id}...")
            except (json.JSONDecodeError, OSError) as e:
                warning(f"{config_file.name} (invalid JSON: {e})")
    
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
    all_configs = get_flat_config_list(CONFIG_DIR)

    if not all_configs:
        error("No existing configs to use as template!")
        click.echo("\nCreate your first config manually in config/ directory.")
        sys.exit(1)

    section_header("CREATE NEW CONFIG")
    click.echo("\n📋 Available templates:\n")

    display_numbered_config_list(all_configs)

    # Get user choice
    click.echo()
    choice = click.prompt('Choose a template (number)', type=int)
    
    if choice < 1 or choice > len(all_configs):
        error("Invalid choice")
        sys.exit(1)

    template_file = all_configs[choice - 1]
    click.echo(f"\n✅ Using template: {click.style(template_file.name, fg='cyan')}")
    
    # Load template
    with open(template_file, 'r', encoding='utf-8') as f:
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
        success("Tab names translated")
    
    # Generate filename
    suffix = '_test' if is_test else ''
    new_filename = f"{apartment_name}_{year}{suffix}.json"
    new_filepath = CONFIG_DIR / new_filename
    
    # Check if file exists
    if new_filepath.exists():
        warning(f"{new_filename} already exists!")
        if not click.confirm('Overwrite?', default=False):
            error("Cancelled")
            return
    
    # Save new config
    with open(new_filepath, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2)
    
    section_header("✅ CONFIG CREATED")
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
    all_configs = get_flat_config_list(CONFIG_DIR)

    if not all_configs:
        error("No configuration files found in config/")
        sys.exit(1)


    section_header("DELETE CONFIGURATION FILES")
    click.echo("\n🗑️  Available configs:\n")

    display_numbered_config_list(all_configs)

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
        error("Invalid input. Use numbers separated by commas.")
        sys.exit(1)
    
    # Validate indices
    invalid = [i for i in indices if i < 1 or i > len(all_configs)]
    if invalid:
        error(f"Invalid selection(s): {', '.join(map(str, invalid))}")
        sys.exit(1)
    
    # Get files to delete
    files_to_delete = [all_configs[i - 1] for i in indices]
    
    # Show confirmation
    click.echo("\n" + "-"*70)
    click.echo("Files to be deleted:\n")
    for f in files_to_delete:
        click.echo(f"  ❌ {click.style(f.name, fg='red')}")
    
    click.echo()
    if not click.confirm(click.style('Are you sure? This cannot be undone!', fg='red', bold=True), default=False):
        warning("Cancelled")
        return
    
    # Delete files
    deleted_count = 0
    for config_file in files_to_delete:
        try:
            config_file.unlink()
            success(f"Deleted: {config_file.name}")
            deleted_count += 1
        except Exception as e:
            error(f"Failed to delete {config_file.name}: {e}")
    
    section_header(f"✅ DELETED {deleted_count} CONFIG(S)")
    click.echo()
