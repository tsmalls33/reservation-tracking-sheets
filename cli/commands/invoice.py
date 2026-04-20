"""Invoice management commands."""

import sys
import json
import subprocess
from datetime import datetime
import click
from .. import PROJECT_ROOT, CONFIG_DIR
from ..utils.config import list_config_files, validate_apartment_config
from ..utils.months import parse_months
from ..utils.completion import complete_apartment, complete_months, complete_year
from ..utils.display import error, success, warning, section_header


@click.group()
def invoice():
    """Manage invoices.
    
    Create invoices from reservation data, list existing invoices,
    and manage invoice templates.
    """
    pass


@invoice.command('config')
def invoice_config():
    """Configure invoice settings for an apartment.
    
    Interactive configuration for apartment invoice details:
    - Invoice code (e.g., MED, SDOM)
    - Client information (landlord)
    - Property name
    
    Choose existing apartment to update or create new configuration.
    """
    invoices_config_path = CONFIG_DIR / "invoices.json"
    
    # Load existing invoice config
    if invoices_config_path.exists():
        with open(invoices_config_path, 'r', encoding='utf-8') as f:
            invoices_config = json.load(f)
    else:
        error("No invoices.json found in config/")
        click.echo("Create the base config file first with template_sheet_id, etc.")
        sys.exit(1)
    
    # Get list of apartments from reservation configs
    reservation_configs = list_config_files(CONFIG_DIR)
    apartment_names = sorted(set(reservation_configs.keys())) if reservation_configs else []
    
    # Get apartments already in invoice config
    existing_invoice_apartments = list(invoices_config.get("apartments", {}).keys())
    
    # Show menu
    section_header("INVOICE CONFIGURATION")
    click.echo("\n📋 Select apartment to configure:\n")
    
    # Option 0: New apartment
    click.echo(f"  {click.style('0.', fg='cyan')} {click.style('[ New Apartment ]', fg='green', bold=True)}")
    
    # Show existing apartments (from reservation configs or invoice configs)
    all_apartments = sorted(set(apartment_names + existing_invoice_apartments))
    
    for idx, apartment in enumerate(all_apartments, 1):
        # Check if has invoice config
        has_invoice = apartment in existing_invoice_apartments
        has_reservation = apartment in apartment_names
        
        badges = []
        if has_invoice:
            badges.append(click.style('[Invoice]', fg='blue'))
        if has_reservation:
            badges.append(click.style('[Reserv]', fg='yellow'))
        
        badge_str = ' '.join(badges) if badges else ''
        click.echo(f"  {idx}. {apartment} {badge_str}")
    
    # Get user selection
    click.echo()
    selection = click.prompt('Select apartment (number)', type=int, default=0)
    
    if selection < 0 or selection > len(all_apartments):
        error("Invalid selection")
        sys.exit(1)
    
    # Determine mode
    is_new = selection == 0
    
    if is_new:
        click.echo(f"\n{click.style('Creating new apartment invoice config', fg='green', bold=True)}")
        apartment_name = click.prompt('\nApartment name (e.g., mediona, sant-domenec)', type=str)
        current_config = {}
    else:
        apartment_name = all_apartments[selection - 1]
        current_config = invoices_config.get("apartments", {}).get(apartment_name, {})
        
        if current_config:
            mode_label = click.style('[UPDATE]', fg='yellow')
            click.echo(f"\n{mode_label} Updating invoice config for: {click.style(apartment_name, fg='cyan', bold=True)}")
            click.echo(f"\n💡 {click.style('Tip:', fg='blue')} Press Enter to keep current value, type space to clear")
        else:
            click.echo(f"\n{click.style('Creating invoice config for:', fg='green', bold=True)} {click.style(apartment_name, fg='cyan', bold=True)}")
    
    # Offer to copy owner info from another config when there's no existing owner data
    owner_fields = ['client_name', 'client_address', 'client_zip_code', 'client_city', 'client_id']
    has_owner_info = any(current_config.get(f) for f in owner_fields)
    
    if not has_owner_info:
        existing_apartments = invoices_config.get("apartments", {})
        configs_with_owner = {
            name: cfg for name, cfg in existing_apartments.items()
            if any(cfg.get(f) for f in owner_fields)
        }
        
        if configs_with_owner:
            click.echo()
            if click.confirm(click.style('Copy owner info from an existing config?', fg='blue'), default=False):
                click.echo(f"\n📋 Available configs with owner info:\n")
                owner_list = sorted(configs_with_owner.keys())
                for idx, name in enumerate(owner_list, 1):
                    client_name = configs_with_owner[name].get('client_name', '')
                    label = f" - {click.style(client_name, fg='yellow')}" if client_name else ''
                    click.echo(f"  {idx}. {name}{label}")
                
                click.echo()
                owner_selection = click.prompt('Select config to copy owner info from', type=int)
                
                if 1 <= owner_selection <= len(owner_list):
                    source_config = configs_with_owner[owner_list[owner_selection - 1]]
                    for field in owner_fields:
                        if source_config.get(field):
                            current_config[field] = source_config[field]
                    
                    is_new = False  # Switch to update mode so user can review/edit copied values
                    click.echo(f"\n{click.style('Owner info copied!', fg='green')} You can review and modify below.")
                    click.echo(f"💡 {click.style('Tip:', fg='blue')} Press Enter to keep current value, type space to clear")
                else:
                    error("Invalid selection, continuing without copying")
    
    # Define invoice configuration fields (matching invoices.json structure)
    fields = [
        {
            'key': 'invoice_code',
            'prompt': 'Invoice Code',
            'help': 'Short code for invoice numbering (e.g., MED, SDOM, GRAN)'
        },
        {
            'key': 'client_name',
            'prompt': 'Client Name',
            'help': 'Landlord/owner full name or company'
        },
        {
            'key': 'client_address',
            'prompt': 'Client Address',
            'help': 'Street address of landlord/owner'
        },
        {
            'key': 'client_zip_code',
            'prompt': 'Client Zip Code',
            'help': 'Postal code'
        },
        {
            'key': 'client_city',
            'prompt': 'Client City',
            'help': 'City name'
        },
        {
            'key': 'client_id',
            'prompt': 'Client ID',
            'help': 'NIF/Tax ID number'
        },
        {
            'key': 'property_name',
            'prompt': 'Property Name',
            'help': 'Full name of the property (appears on invoice)'
        }
    ]
    
    # Collect configuration
    click.echo("\n" + "-"*70)
    click.echo("Enter configuration details:\n")
    
    new_config = {}
    
    for field in fields:
        key = field['key']
        prompt_text = field['prompt']
        help_text = field.get('help', '')
        
        current_value = current_config.get(key, '')
        
        # Show current value if updating
        if not is_new and current_value:
            click.echo(f"\n{click.style(prompt_text, fg='cyan')}")
            click.echo(f"  Current: {click.style(str(current_value), fg='yellow')}")
            click.echo(f"  ({help_text})")
            
            user_input = click.prompt('  New value (Enter=keep, space=clear)', 
                                     default='', 
                                     show_default=False,
                                     type=str)
            
            # Handle input
            if user_input == '':
                # Keep existing
                new_config[key] = current_value
            elif user_input.strip() == '':
                # Single space = clear
                new_config[key] = ''
            else:
                # New value
                new_config[key] = user_input
        else:
            # New field or no current value
            click.echo(f"\n{click.style(prompt_text, fg='cyan')}")
            click.echo(f"  ({help_text})")
            
            user_input = click.prompt('  Value', 
                                     default='', 
                                     show_default=False,
                                     type=str)
            
            new_config[key] = user_input.strip() if user_input else ''
    
    # Update config
    if "apartments" not in invoices_config:
        invoices_config["apartments"] = {}
    
    invoices_config["apartments"][apartment_name] = new_config
    
    # Save to file
    with open(invoices_config_path, 'w', encoding='utf-8') as f:
        json.dump(invoices_config, f, indent=2)
    
    # Show summary
    section_header("✅ CONFIGURATION SAVED")
    click.echo(f"Apartment: {click.style(apartment_name, fg='cyan', bold=True)}")
    click.echo(f"Config file: {invoices_config_path}")
    
    click.echo("\n📋 Configured fields:")
    for field in fields:
        key = field['key']
        value = new_config.get(key, '')
        if value:
            display_value = str(value)
            if len(display_value) > 50:
                display_value = display_value[:47] + "..."
            click.echo(f"  ✓ {field['prompt']}: {display_value}")
        else:
            click.echo(f"  ○ {field['prompt']}: {click.style('(empty)', fg='yellow')}")
    
    click.echo(f"\n💡 Use this config with: {click.style(f'rez invoice create -a {apartment_name} -m jan', fg='cyan')}")
    click.echo()


@invoice.command('create')
@click.option('--apartment', '-a', required=True,
              shell_complete=complete_apartment, help='Apartment name')
@click.option('--months', '-m', required=True,
              shell_complete=complete_months,
              help='Months (jan,feb or q1,q2 or all)')
@click.option('--year', '-y', type=int, default=datetime.now().year,
              shell_complete=complete_year, help='Year (default: current year)')
@click.option('--email', '-e', help='Email to share invoice with')
@click.option('--invoice-number', '-n', default=None,
              help="Custom invoice number to use verbatim instead of auto-generating.")
@click.option('--test', is_flag=True,
              help='Use test reservation config and TEST_ invoice numbering')
def invoice_create(apartment, months, year, email, invoice_number, test):
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
      rez invoice create -a mediona -m jan -y 2025

      # Test invoice (uses test config, TEST_ numbering)
      rez invoice create -a mediona -m jan -y 2025 --test

      # Multiple months
      rez invoice create -a mediona -m jan,feb,mar -y 2025

      # Quarter
      rez invoice create -a mediona -m q1 -y 2025

      # Full year
      rez invoice create -a mediona -m all -y 2025

      # With email sharing
      rez invoice create -a mediona -m q1 -y 2025 -e your@email.com
    """
    try:
        # Validate custom invoice number (if provided) before doing any work
        if invoice_number is not None:
            invoice_number = invoice_number.strip()
            if not invoice_number:
                error("--invoice-number cannot be empty")
                sys.exit(1)

        # Validate apartment config exists before doing any work
        validate_apartment_config(CONFIG_DIR, apartment, year, test)

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

        if invoice_number:
            cmd.extend(['--invoice-number', invoice_number])

        subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)

    except ValueError as e:
        error(str(e))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        error("Invoice creation failed!")
        if e.stderr:
            click.echo(e.stderr, err=True)
        sys.exit(1)


@invoice.command('list')
@click.option('--apartment', '-a',
              shell_complete=complete_apartment, help='Filter by apartment')
def invoice_list(apartment):
    """List all generated invoices.
    
    Shows invoice numbers, dates, months covered, and spreadsheet links.
    Optionally filter by apartment.
    """
    invoices_dir = PROJECT_ROOT / "invoices"
    
    if not invoices_dir.exists():
        error("No invoices directory found")
        sys.exit(1)
    
    # Collect all invoices
    all_invoices = []
    
    if apartment:
        # Filter by apartment
        apartment_dir = invoices_dir / apartment
        if apartment_dir.exists():
            for invoice_file in apartment_dir.glob('*.json'):
                try:
                    with open(invoice_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['apartment'] = apartment
                        all_invoices.append(data)
                except (json.JSONDecodeError, OSError):
                    pass
    else:
        # All apartments
        for apartment_dir in invoices_dir.iterdir():
            if apartment_dir.is_dir():
                for invoice_file in apartment_dir.glob('*.json'):
                    try:
                        with open(invoice_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            all_invoices.append(data)
                    except (json.JSONDecodeError, OSError):
                        pass
    
    if not all_invoices:
        warning("No invoices found")
        click.echo(f"\nCreate one with: {click.style('rez invoice create -a mediona -m jan', fg='cyan')}")
        return
    
    # Sort by created date
    all_invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Display
    section_header("INVOICES")
    
    for inv in all_invoices:
        is_test = inv.get('test_mode', False)
        badge = click.style('[TEST]', fg='yellow') if is_test else click.style('[PROD]', fg='green')
        
        click.echo(f"\n{badge} {click.style(inv['invoice_number'], fg='cyan', bold=True)}")
        click.echo(f"   Apartment: {inv['apartment']}")
        click.echo(f"   Months: {', '.join([m.capitalize() for m in inv['months']])}")
        click.echo(f"   Year: {inv['year']}")
        click.echo(f"   Created: {inv['created_at'][:10]}")
        owner_info = inv.get('owner_info', {})
        if owner_info and owner_info.get('client_name'):
            click.echo(f"   Owner: {owner_info['client_name']}")
    
    click.echo(f"\n📊 Total: {len(all_invoices)} invoice(s)")
    click.echo()
