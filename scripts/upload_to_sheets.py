

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from pathlib import Path
import sys
import json
import argparse
from datetime import datetime
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")

def print_header(title, char="="):
    """Print a styled header."""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}")

def print_step(emoji, message, indent=0):
    """Print a step with consistent formatting."""
    spaces = "  " * indent
    print(f"{spaces}{emoji} {message}")

def print_success(message, indent=0):
    """Print success message."""
    spaces = "  " * indent
    print(f"{spaces}✅ {message}")

def print_info(message, indent=1):
    """Print info message."""
    spaces = "  " * indent
    print(f"{spaces}→ {message}")

def get_tab_name(config, tab_key):
    """Get tab name with whitespace stripped."""
    return config['tabs'][tab_key]['tab_name'].strip()

def get_worksheet_fuzzy(spreadsheet, target_name):
    """Find worksheet by name, ignoring whitespace."""
    target_clean = target_name.strip()
    for ws in spreadsheet.worksheets():
        if ws.title.strip() == target_clean:
            return ws
    raise gspread.exceptions.WorksheetNotFound(target_name)

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
    
    print_step("🔍", f"Looking for config: {apartment_name}_{year}{suffix}.json")
    
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        print_success(f"Config loaded")
        print_info(f"Spreadsheet: {config['spreadsheet_id'][:20]}...")
        print_info(f"Tabs defined: {len(config.get('tabs', {}))}")
        return config
    else:
        available = list_config_files()
        error_msg = f"❌ Config not found: {config_path}\n"
        if available:
            error_msg += f"📋 Available: {', '.join(available)}\n"
        raise FileNotFoundError(error_msg)

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    print_step("🔐", "Authenticating with Google Sheets...")
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = PROJECT_ROOT / 'credentials/service_account.json'
    
    if not creds_path.exists():
        raise FileNotFoundError(f"❌ Credentials not found: {creds_path}")
    
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    client = gspread.authorize(creds)
    print_success("Authenticated")
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
    
    return [month_map[m] for m in months if m in month_map], months

def clear_exact_range(worksheet, start_cell, num_cols, num_rows):
    """Clear VALUES ONLY, preserve formatting/data validation."""
    end_cell = chr(ord(start_cell[0]) + num_cols - 1) + str(int(start_cell[1:]) + num_rows - 1)
    range_str = f"{start_cell}:{end_cell}"
    worksheet.batch_clear([range_str])

def upload_reservations(client, config, spreadsheet_id, csv_file, hard_replace=False):
    """Upload processed reservations to auto-detected months."""
    
    print_header("📊 UPLOAD SUMMARY", "=")
    
    # Read CSV
    df = pd.read_csv(csv_file)
    print_step("📂", f"Loaded {len(df)} reservations from CSV")
    
    # Convert dates
    df['Entrada'] = pd.to_datetime(df['Entrada']).dt.strftime('%Y-%m-%d')
    df['Salida'] = pd.to_datetime(df['Salida']).dt.strftime('%Y-%m-%d')
    
    # Detect months
    target_tabs, month_names = detect_months_from_csv(csv_file)
    print_step("📅", f"Target months: {', '.join([m.capitalize() for m in month_names])}")
    
    # Open spreadsheet
    print_step("🔗", "Connecting to Google Sheets...")
    spreadsheet = client.open_by_key(spreadsheet_id)
    print_success(f"Connected: '{spreadsheet.title}'")
    
    # Get available tabs
    available_tabs = {ws.title.strip() for ws in spreadsheet.worksheets()}
    
    # Clear phase
    print_header("🧹 CLEARING PHASE", "-")
    
    if hard_replace:
        print_info("Mode: Hard replace (all tabs)")
        tabs_to_clear = [k for k in config['tabs'] if '_reservations' in k]
    else:
        print_info("Mode: Smart clear (detected months only)")
        tabs_to_clear = target_tabs
    
    cleared_count = 0
    for tab_key in tabs_to_clear:
        tab_name = get_tab_name(config, tab_key)
        if tab_name not in available_tabs:
            continue
        try:
            ws = get_worksheet_fuzzy(spreadsheet, tab_name)
            clear_exact_range(ws, config['tabs'][tab_key]['start_range'], 
                            len(config['tabs'][tab_key]['columns']), 15)
            print_info(f"{tab_name}: Cleared", indent=1)
            cleared_count += 1
        except gspread.exceptions.WorksheetNotFound:
            continue
    
    print_success(f"Cleared {cleared_count} tabs")
    
    # Upload phase
    print_header("📤 UPLOAD PHASE", "-")
    
    df['month_name'] = pd.to_datetime(df['Entrada']).dt.strftime('%B').str.lower()
    df = df.replace([float('inf'), float('-inf')], pd.NA).fillna('')
    
    total_uploaded = 0
    
    for tab_key in target_tabs:
        tab_name = get_tab_name(config, tab_key)
        
        if tab_name not in available_tabs:
            continue
        
        month_data = df[df['month_name'] == tab_key.split('_')[0]]
        month_name = month_data['month_name'].iloc[0].capitalize() if not month_data.empty else tab_key.split('_')[0].capitalize()
        
        try:
            worksheet = get_worksheet_fuzzy(spreadsheet, tab_name)
        except gspread.exceptions.WorksheetNotFound:
            continue

        # Update B2 with month name
        worksheet.update(values=[[month_name]], range_name='B2', value_input_option='USER_ENTERED')
        
        if len(month_data) > 0:
            columns = config['tabs'][tab_key]['columns']
            
            processed_rows = []
            for _, row in month_data.iterrows():
                row_list = ['' for _ in columns]
                row_list[0] = str(row['Actividad'])
                row_list[1] = ''
                row_list[2] = str(row['Entrada'])
                row_list[3] = str(row['Salida'])
                row_list[4] = str(row['Noches'])
                row_list[5] = str(row['Precio'])
                row_list[6] = str(row['Check In/Out'])
                row_list[7] = str(row['Comision'])
                processed_rows.append(row_list)
            
            start_cell = config['tabs'][tab_key]['start_range']
            worksheet.update(values=processed_rows, range_name=start_cell, value_input_option='USER_ENTERED')
            print_step("✓", f"{month_name}: {len(processed_rows)} reservations", indent=1)
            total_uploaded += len(processed_rows)
    
    print_header("🎉 COMPLETE", "=")
    print_step("📊", f"Total uploaded: {total_uploaded} reservations")
    print_step("📅", f"Months updated: {len(target_tabs)}")
    print_step("🗂️", f"Spreadsheet: {spreadsheet.title}")

def print_help():
    """Print help from USAGE.txt file."""
    usage_file = PROJECT_ROOT / 'USAGE.txt'
    if usage_file.exists():
        print(usage_file.read_text())
    else:
        print("❌ USAGE.txt not found.")

def main():
    parser = argparse.ArgumentParser(
        description="Upload processed CSV to Google Sheets", 
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--csv', required=True, help="Path to processed CSV")
    parser.add_argument('--apartment', required=True, help="Apartment name")
    parser.add_argument('--year', type=int, default=2026, help="Year (default: 2026)")
    parser.add_argument('--hard-replace', action='store_true', help="Clear ALL tabs")
    parser.add_argument('--test', action='store_true', help="Use test config")
    
    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        print_help()
        return
    
    args = parser.parse_args()
    
    print_header("🚀 RESERVATION UPLOADER", "=")
    print_info(f"Apartment: {args.apartment}")
    print_info(f"Year: {args.year}")
    print_info(f"Mode: {'Test' if args.test else 'Production'}")
    print_info(f"Replace: {'Hard' if args.hard_replace else 'Smart'}")
    
    config = load_config(args.apartment, args.year, args.test)
    client = authenticate_sheets()
    
    upload_reservations(client, config, config['spreadsheet_id'], args.csv, args.hard_replace)

if __name__ == "__main__":
    main()



