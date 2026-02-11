#!/usr/bin/env python3
"""
Reservations CLI - Process & Upload Airbnb/Booking data to Google Sheets
"""

import click
import subprocess
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")


# HELPER FUNCTIONS (top level)
def detect_platform(filename):
    fn_lower = Path(filename).name.lower()
    
    if any(x in fn_lower for x in ['airbnb', 'confirmación', 'hm']):
        return 'airbnb'
    if any(x in fn_lower for x in ['booking', 'reservation', 'invoice']):
        return 'booking'
    
    # Quick content check if needed
    content = Path(filename).read_text(errors='ignore')[:1000].lower()
    if any(x in content for x in ['airbnb', 'confirmación', 'hm']):
        return 'airbnb'
    if any(x in content for x in ['booking', 'reservation number', 'invoice number']):
        return 'booking'
    
    raise ValueError(f"Unknown platform: {filename}")


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
    script_path = PROJECT_ROOT / f"scripts/process_{platform}.py"
    output_file = Path(output or PROJECT_ROOT / f"data/processed/{platform}_processed.csv")
    
    click.echo(f"🔄 Processing {platform} CSV: {csv_file}")
    click.echo(f"📤 Output: {output_file}")
    
    result = subprocess.run([
        sys.executable, str(script_path), csv_file, str(output_file)
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
    upload_script = PROJECT_ROOT / "scripts/upload_to_sheets.py"
    
    cmd = [
        sys.executable, str(upload_script),
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


@cli.command()
@click.argument('csv_files', nargs=-1, type=click.Path(exists=True))
@click.option('--apartment', '-a', required=True)
@click.option('--year', '-y', type=int, default=2026)
@click.option('--test', is_flag=True)
@click.option('--hard-replace', '-H', is_flag=True)
def oneshot(csv_files, apartment, year, test, hard_replace):
    """Process + merge + upload in one command."""
    if not csv_files:
        click.echo("Error: Provide at least one CSV")
        sys.exit(1)
    
    temp_dir = PROJECT_ROOT / "data" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    processed_files = []
    for csv_file in csv_files:
        platform = detect_platform(csv_file)
        script_path = PROJECT_ROOT / f"scripts/process_{platform}.py"
        processed = temp_dir / f"{platform}_processed.csv"
        
        click.echo(f"🔄 Processing {platform}: {csv_file}")
        subprocess.run([
            sys.executable, str(script_path), 
            str(csv_file), str(processed)
        ], check=True)
        processed_files.append(processed)
    
    # Merge if multiple files
    if len(processed_files) > 1:
        merge_script = PROJECT_ROOT / "scripts/merge_data.py"
        merged = temp_dir / f"{apartment}_{year}_merged.csv"
        
        click.echo(f"🔀 Merging {len(processed_files)} files...")
        subprocess.run([
            sys.executable, str(merge_script),
            *[str(f) for f in processed_files], str(merged)
        ], check=True)
        final_csv = merged
    else:
        final_csv = processed_files[0]
    
    # Upload
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
    
    click.echo(f"📤 Uploading to {apartment} {year}...")
    subprocess.run(cmd, check=True)
    click.echo(click.style(f"✅ Complete! Uploaded to {apartment}_{year}{'_test' if test else ''}", fg="green"))


if __name__ == '__main__':
    cli()

