#!/usr/bin/env python3
"""
Reservations CLI - Process & Upload Airbnb/Booking data to Google Sheets
"""

import click
import subprocess
import sys
from pathlib import Path
import os

@click.group()
@click.version_option("1.0.0")
def cli():
    """Manage reservation data from Airbnb/Booking to Google Sheets."""
    pass

@cli.command()
@click.argument('platform', type=click.Choice(['airbnb', 'booking']))
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), 
              help='Output processed CSV (default: data/processed)')
def process(platform, csv_file, output):
    """Process raw CSV from Airbnb/Booking."""
    script_map = {
        'airbnb': 'scripts/process_airbnb.py',
        'booking': 'scripts/process_booking.py'
    }
    
    script = script_map[platform]
    output_file = Path(output or f"data/processed/{platform}_processed.csv")
    
    click.echo(f"🔄 Processing {platform} CSV: {csv_file}")
    click.echo(f"📤 Output: {output_file}")
    
    result = subprocess.run([
        sys.executable, script, csv_file, str(output_file)
    ], check=True, capture_output=True, text=True)
    
    click.echo(click.style("✅ Processing complete!", fg="green"))

@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--apartment', '-a', required=True, help="Apartment name")
@click.option('--year', '-y', type=int, default=2026)
@click.option('--test', is_flag=True, help="Use test config (_test.json)")
@click.option('--hard-replace', '-H', is_flag=True, help="Clear ALL tabs")
def upload(csv_file, apartment, year, test, hard_replace):
    """Upload processed CSV to Google Sheets."""
    cmd = [
        sys.executable, 'scripts/upload_to_sheets.py',
        '--csv', str(csv_file),
        '--apartment', apartment,
        '--year', str(year)
    ]
    
    if test:
        cmd.append('--test')
    if hard_replace:
        cmd.append('--hard-replace')
    
    click.echo(f"📤 Uploading {csv_file} → {apartment}_{year}{'_test' if test else ''}")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    click.echo(click.style("✅ Upload complete!", fg="green"))

if __name__ == '__main__':
    cli()
