"""Commands for opening the project in Neovim or viewing Google Sheets."""

import os
import sys
import json
import click
from pathlib import Path
from .. import PROJECT_ROOT, CONFIG_DIR
from ..utils.completion import complete_apartment, complete_year
from ..utils.display import error, success, info


@click.command('open')
@click.option('--apartment', '-a',
              shell_complete=complete_apartment,
              help='Open Google Sheet for apartment (e.g., mediona, sant-domenec)')
@click.option('--year', '-y', type=int, default=2026,
              shell_complete=complete_year,
              help='Year for apartment config (default: 2026)')
@click.option('--test', is_flag=True, help='Use test configuration')
def open_cmd(apartment, year, test):
    """Open the project in Neovim or view apartment Google Sheet.
    
    Without options: Opens the project root in Neovim.
    With --apartment: Displays clickable link to the Google Sheet.
    
    \b
    Examples:
      # Open project in Neovim
      reservations open
      
      # View Mediona 2026 Google Sheet link
      reservations open -a mediona
      
      # View Sant Domènec 2026 test sheet link
      reservations open -a sant-domenec --test
      
      # View specific year
      reservations open -a mediona -y 2025
    
    \b
    Note:
      The Google Sheet link is clickable in most terminals.
      Click it or copy/paste into your browser.
    """
    
    # If apartment specified, show Google Sheet link
    if apartment:
        suffix = '_test' if test else ''
        config_file = CONFIG_DIR / f"{apartment}_{year}{suffix}.json"
        
        if not config_file.exists():
            error(f"Config not found: {apartment}_{year}{suffix}.json")
            
            # List available configs
            available = [f.stem for f in CONFIG_DIR.glob('*.json') if f.stem != 'invoices']
            if available:
                click.echo("\n📋 Available configurations:")
                for cfg in sorted(available):
                    click.echo(f"  • {cfg}")
            sys.exit(1)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            spreadsheet_id = config.get('spreadsheet_id')
            if not spreadsheet_id:
                error("No spreadsheet_id found in config")
                sys.exit(1)
            
            # Build Google Sheets URL
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            
            mode = "TEST" if test else "PRODUCTION"
            click.echo(f"\n📊 {click.style(apartment.upper(), fg='cyan')} {year} ({mode})")
            click.echo(f"\n🔗 Google Sheet:")
            click.echo(f"   {click.style(sheet_url, fg='blue', underline=True)}")
            click.echo()
            info("Click the link or copy/paste into your browser")
            
        except json.JSONDecodeError:
            error(f"Invalid JSON in config: {config_file}")
            sys.exit(1)
        except Exception as e:
            error(f"Error reading config: {e}")
            sys.exit(1)
    
    else:
        # Default behavior: open project in Neovim
        click.echo(f"📂 Opening project in Neovim: {click.style(str(PROJECT_ROOT), fg='cyan')}")
        try:
            # Use os.execvp to replace the current process with nvim
            # This allows nvim to take over the terminal properly
            os.chdir(PROJECT_ROOT)
            os.execvp('nvim', ['nvim', str(PROJECT_ROOT)])
        except FileNotFoundError:
            error("nvim not found. Make sure Neovim is installed.")
            sys.exit(1)
        except Exception as e:
            error(f"Error opening Neovim: {e}")
            sys.exit(1)


