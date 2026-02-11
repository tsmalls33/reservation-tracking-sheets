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
from pathlib import Path

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")


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
