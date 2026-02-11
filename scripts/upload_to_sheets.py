import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from pathlib import Path
import sys
import json
import argparse
from datetime import datetime
import os

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")

def list_config_files():
    """List all JSON config files in config/ directory."""
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        configs = [f for f in config_dir.glob('*.json')]
        return [f.name for f in configs]
    return []

def load_config(apartment_name, year, test_mode=False):
    """Load config with smart defaults and test mode support."""
    suffix = '_test' if test_mode else ''
    config_path = PROJECT_ROOT / f"config/{apartment_name}_{year}{suffix}.json"
    
    if Path(config_path).exists():
        print(f"📁 Using config: {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        available = list_config_files()
        error_msg = f"❌ Config not found: {config_path}\n"
        if available:
            error_msg += f"📋 Available configs: {', '.join(available)}\n"
        else:
            error_msg += "📁 No config files found in config/ directory\n"
        error_msg += "💡 Run: python scripts/upload_to_sheets.py --help"
        raise FileNotFoundError(error_msg)

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = PROJECT_ROOT / 'credentials/service_account.json'  # ← ABSOLUTE PATH
    
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    client = gspread.authorize(creds)
    return client

def detect_months_from_csv(csv_file):
    """Auto-detect which months are present in CSV based on check-in dates."""
    df = pd.read_csv(csv_file)
    df['Entrada'] = pd.to_datetime(df['Entrada'])
    df['month'] = df['Entrada'].dt.strftime('%B').str.lower()
    months = df['month'].unique()
    
    month_map = {
        'january': 'january_reservations',
        'february': 'february_reservations',
        'march': 'march_reservations',
        'april': 'april_reservations',
        'may': 'may_reservations',
        'june': 'june_reservations',
        'july': 'july_reservations',
        'august': 'august_reservations',
        'september': 'september_reservations',
        'october': 'october_reservations',
        'november': 'november_reservations',
        'december': 'december_reservations'
    }
    
    return [month_map[m] for m in months if m in month_map]

def clear_exact_range(worksheet, start_cell, num_cols, num_rows):
    """Clear VALUES ONLY, preserve formatting/data validation."""
    end_cell = chr(ord(start_cell[0]) + num_cols - 1) + str(int(start_cell[1:]) + num_rows - 1)
    range_str = f"{start_cell}:{end_cell}"
    
    # batch_clear preserves formatting! [web:77]
    worksheet.batch_clear([range_str])
    print(f"✂️  Cleared values only: {range_str} (formatting preserved)")

def upload_reservations(client, config, spreadsheet_id, csv_file, hard_replace=False):
    """Upload processed reservations to auto-detected months."""
    df = pd.read_csv(csv_file)
    
    # Convert dates to strings for JSON serialization
    df['Entrada'] = pd.to_datetime(df['Entrada']).dt.strftime('%Y-%m-%d')
    df['Salida'] = pd.to_datetime(df['Salida']).dt.strftime('%Y-%m-%d')
    
    # Auto-detect months from CSV
    target_tabs = detect_months_from_csv(csv_file)
    print(f"📅 Detected months in CSV: {[t.split('_')[0] for t in target_tabs]}")
    
    # Clear logic
    if hard_replace:
        print("🔥 HARD REPLACE MODE: Clearing ALL reservation tabs...")
        for tab_key in config['tabs']:
            if '_reservations' in tab_key:
                ws = client.open_by_key(spreadsheet_id).worksheet(config['tabs'][tab_key]['tab_name'])
                clear_exact_range(ws, config['tabs'][tab_key]['start_range'], len(config['tabs'][tab_key]['columns']), 15)
    else:
        print("✂️  Normal mode: Clearing only detected month tabs...")
        for tab_key in target_tabs:
            ws = client.open_by_key(spreadsheet_id).worksheet(config['tabs'][tab_key]['tab_name'])
            clear_exact_range(ws, config['tabs'][tab_key]['start_range'], len(config['tabs'][tab_key]['columns']), 15)
    
    # Group data by month and upload (dates already strings)
    df['month_name'] = pd.to_datetime(df['Entrada']).dt.strftime('%B').str.lower()
    
    # Replace NaN/inf with empty strings, ensure JSON-safe data
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    df = df.fillna('')
    
    for tab_key in target_tabs:
        month_data = df[df['month_name'] == tab_key.split('_')[0]]
        month_name = month_data['month_name'].iloc[0].capitalize() if not month_data.empty else tab_key.split('_')[0].capitalize()
        worksheet = client.open_by_key(spreadsheet_id).worksheet(config['tabs'][tab_key]['tab_name'])

        # Update B2 with month name
        worksheet.update(values=[[month_name]], range_name='B2', value_input_option='USER_ENTERED')
        print(f"📝 Updated {config['tabs'][tab_key]['tab_name']} B2: {month_name}")
        if len(month_data) > 0:
            columns = config['tabs'][tab_key]['columns']
            
            processed_rows = []
            for _, row in month_data.iterrows():
                row_list = ['' for _ in columns]  # Start with 8 empty cells
                
                # Map data correctly to sheet columns (F=0, G=1, H=2...)
                row_list[0] = str(row['Actividad'])  # F: Guest name
                row_list[1] = ''                     # G: Empty (F:G merge)
                row_list[2] = str(row['Entrada'])    # H: Check-in  
                row_list[3] = str(row['Salida'])     # I: Check-out
                row_list[4] = str(row['Noches'])     # J: Nights
                row_list[5] = str(row['Precio'])     # K: Price
                row_list[6] = str(row['Check In/Out']) # L: Cleaning
                row_list[7] = str(row['Comision'])   # M: Commission
                # VAT (N) left empty for formulas
                
                processed_rows.append(row_list)
            
            data = processed_rows  # No headers
            
            worksheet = client.open_by_key(spreadsheet_id).worksheet(config['tabs'][tab_key]['tab_name'])
            start_cell = config['tabs'][tab_key]['start_range']
            
            worksheet.update(values=data, range_name=start_cell, value_input_option='USER_ENTERED')
        print(f"✓ Uploaded {len(processed_rows)} reservations to {config['tabs'][tab_key]['tab_name']}")
    
    print(f"🎉 Processed {len(df)} total reservations across {len(target_tabs)} months")

def print_help():
    """Print help from USAGE.txt file."""
    usage_file = Path('USAGE.txt')
    if usage_file.exists():
        print(usage_file.read_text())
    else:
        print("❌ USAGE.txt not found. Create it with usage instructions.")

def main():
    parser = argparse.ArgumentParser(
        description="Upload processed CSV to Google Sheets", 
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/upload_to_sheets.py --csv data/processed.csv
  python scripts/upload_to_sheets.py --csv data.csv --hard-replace
        """
    )
    parser.add_argument('--csv', required=True, help="Path to processed CSV")
    parser.add_argument('--apartment', required=True, help="Apartment name (e.g. 'part_alta')")
    parser.add_argument('--year', type=int, default=2026, help="Year (default: 2026)")
    parser.add_argument('--hard-replace', action='store_true', help="Clear ALL reservation tabs")
    parser.add_argument('--test', action='store_true', help="Use test config (appends '_test')")
    
    # Handle --help alone
    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        print_help()
        return
    
    args = parser.parse_args()
    
    # Load config and authenticate
    config = load_config(args.apartment, args.year, args.test)
    client = authenticate_sheets()
    
    # Upload
    upload_reservations(client, config, config['spreadsheet_id'], args.csv, args.hard_replace)

if __name__ == "__main__":
    main()
