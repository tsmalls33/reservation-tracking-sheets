"""Command for viewing documentation."""

import click

DOCS_URL = "https://github.com/tsmalls33/reservation-tracking-sheets/tree/main/docs"


@click.command()
def docs():
    """View online documentation.
    
    Opens a link to the GitHub documentation folder where you can find
    detailed guides for installation, configuration, invoices, and more.
    
    \b
    Available Documentation:
      • INSTALLATION.md - Setup and Google Cloud configuration
      • CONFIGURATION.md - Apartment configs and column mappings
      • INVOICES.md - Invoice generation and management
      • DATA_MANAGEMENT.md - File handling and cleanup
      • CLI_ARCHITECTURE.md - Technical architecture details
    
    \b
    Example:
      rez docs
    """
    click.echo("\n📚 Reservation Tracking Documentation\n")
    click.echo(f"🔗 {click.style(DOCS_URL, fg='blue', underline=True)}\n")
    click.echo("💡 Click the link or copy/paste into your browser\n")
