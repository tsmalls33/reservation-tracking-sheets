"""Reservation Tracking CLI - Main entry point."""

import click
from pathlib import Path

# Project root - available to all CLI modules
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CONFIG_DIR = PROJECT_ROOT / "config"

__version__ = "2.0.0"


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx):
    """Reservation Tracking System - Automate Airbnb/Booking.com to Google Sheets.
    
    Intelligent CSV processing and upload tool for vacation rental managers.
    Automatically detects platforms, standardizes data, and uploads to Google Sheets
    with configurable column mappings.
    
    \b
    Features:
    • Auto-detects Airbnb and Booking.com formats
    • Processes multiple CSVs in one command (auto-merge)
    • Dynamic column mapping per apartment
    • Multi-language support (English/Spanish)
    • Calculated fields (sum, formulas)
    • Smart clearing (only modified months)
    • Invoice generation with PDF export
    • Auto-cleanup temporary files
    
    \b
    Quick Start:
      reservations upload bookings.csv -a downtown-loft
      reservations invoice create -a downtown-loft -m january,february
      reservations open -a downtown-loft
      reservations docs
    
    \b
    Configuration:
      Configs: config/{apartment}_{year}.json
      Each defines spreadsheet ID, tabs, columns, and mappings.
    
    \b
    Documentation:
      Run 'reservations docs' to view full documentation online.
      Or see docs/ folder for detailed guides:
      • INSTALLATION.md - Setup and Google Cloud configuration
      • CONFIGURATION.md - Apartment config and column mappings
      • INVOICES.md - Invoice generation and management
      • CLI_ARCHITECTURE.md - Technical architecture details

    \b
    Shell Completion:
      Enable tab-completion (add to your shell profile):
        bash: eval "$(_RESERVATIONS_COMPLETE=bash_source reservations)"
        zsh:  eval "$(_RESERVATIONS_COMPLETE=zsh_source reservations)"
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj['project_root'] = PROJECT_ROOT
    ctx.obj['config_dir'] = CONFIG_DIR


def register_commands():
    """Register all command groups and commands."""
    from .commands import config, invoice, upload, open_project, docs
    
    cli.add_command(config.config)
    cli.add_command(invoice.invoice)
    cli.add_command(upload.upload)
    cli.add_command(open_project.open_cmd)
    cli.add_command(docs.docs)


# Register commands on import
register_commands()
