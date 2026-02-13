"""Upload command for processing and uploading reservation data."""

import sys
import subprocess
import click
from pathlib import Path
from .. import PROJECT_ROOT
from ..utils.platform import detect_platform
from ..utils.display import error, success, section_header


@click.command()
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
        error("Provide at least one CSV file")
        sys.exit(1)
    
    # Create temp directory
    temp_dir = PROJECT_ROOT / "data" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each CSV
    processed_files = []
    section_header("PROCESSING CSVs")
    
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
            success("Processed")
            
        except ValueError as e:
            error(str(e))
            sys.exit(1)
        except subprocess.CalledProcessError:
            error(f"Processing failed for {csv_file}")
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
        success("Merged")
    else:
        final_csv = processed_files[0]
    
    # Upload
    section_header("UPLOADING TO GOOGLE SHEETS")
    
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
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        
        section_header("✅ SUCCESS")
        click.echo(f"Uploaded to: {apartment}_{year}{config_suffix}")
        click.echo()
        
    except subprocess.CalledProcessError:
        section_header("❌ UPLOAD FAILED")
        sys.exit(1)
