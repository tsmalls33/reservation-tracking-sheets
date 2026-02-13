"""Reservation Tracking CLI - Main entry point."""

import click
from pathlib import Path

# Project root - available to all CLI modules
PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")
CONFIG_DIR = PROJECT_ROOT / "config"

__version__ = "2.0.0"


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx):
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
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj['project_root'] = PROJECT_ROOT
    ctx.obj['config_dir'] = CONFIG_DIR


def register_commands():
    """Register all command groups and commands."""
    from .commands import config, invoice, upload, open_project
    
    cli.add_command(config.config)
    cli.add_command(invoice.invoice)
    cli.add_command(upload.upload)
    cli.add_command(open_project.open_cmd)
    cli.add_command(open_project.source)


# Register commands on import
register_commands()
