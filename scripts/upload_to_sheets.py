

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

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Month name translations
MONTH_NAMES = {
    'january': {'en': 'January', 'es': 'Enero'},
    'february': {'en': 'February', 'es': 'Febrero'},
    'march': {'en': 'March', 'es': 'Marzo'},
    'april': {'en': 'April', 'es': 'Abril'},
    'may': {'en': 'May', 'es': 'Mayo'},
    'june': {'en': 'June', 'es': 'Junio'},
    'july': {'en': 'July', 'es': 'Julio'},
    'august': {'en': 'August', 'es': 'Agosto'},
    'september': {'en': 'September', 'es': 'Septiembre'},
    'october': {'en': 'October', 'es': 'Octubre'},
    'november': {'en': 'November', 'es': 'Noviembre'},
    'december': {'en': 'December', 'es': 'Diciembre'}
}

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

def get_month_name_for_display(month_key, language='en'):
    """Get the display name for a month in the specified language.
    
    Args:
        month_key: Month key like 'january', 'february', etc.
        language: 'en' for English or 'es' for Spanish
    
    Returns:
        Capitalized month name in the specified language
    """
    if month_key in MONTH_NAMES:
        return MONTH_NAMES[month_key].get(language, MONTH_NAMES[month_key]['en'])
    return month_key.capitalize()

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
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print_success(f"Config loaded")
        print_info(f"Spreadsheet: {config['spreadsheet_id'][:20]}...")
        print_info(f"Tabs defined: {len(config.get('tabs', {}))}")
        
        # Detect language from config or default to English
        language = config.get('language', 'en')
        if language not in ['en', 'es']:
            language = 'en'
        config['_language'] = language
        print_info(f"Language: {language.upper()}")
        
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
    """Clear VALUES ONLY, preserve formatting/data validation.
    
    Args:
        worksheet: gspread worksheet
        start_cell: Starting cell (e.g., 'F11')
        num_cols: Number of physical columns to clear
        num_rows: Number of rows to clear
    """
    start_col_letter = ''.join(filter(str.isalpha, start_cell))
    start_row = int(''.join(filter(str.isdigit, start_cell)))
    
    # Calculate end column letter
    start_col_num = ord(start_col_letter.upper()) - ord('A') + 1
    end_col_num = start_col_num + num_cols - 1
    end_col_letter = chr(ord('A') + end_col_num - 1)
    
    end_row = start_row + num_rows - 1
    range_str = f"{start_cell}:{end_col_letter}{end_row}"
    
    worksheet.batch_clear([range_str])

def build_row_from_mapping(row_data, column_mapping, columns):
    """Build a row list dynamically based on column_mapping config.
    
    Supports both single field mapping and calculated fields (e.g., sum of multiple fields).
    
    Args:
        row_data: pandas Series with CSV data
        column_mapping: dict mapping column names to their config
        columns: ordered list of column names from config
    
    Returns:
        List of values positioned according to sheet_col_offset
    """
    # Find max offset to determine row size
    max_offset = max(col_cfg['sheet_col_offset'] for col_cfg in column_mapping.values())
    row_list = [''] * (max_offset + 1)
    
    for col_name in columns:
        if col_name not in column_mapping:
            continue
        
        col_cfg = column_mapping[col_name]
        offset = col_cfg['sheet_col_offset']
        
        # Check if this is a calculated field (multiple csv_fields with operation)
        if 'csv_fields' in col_cfg and 'operation' in col_cfg:
            csv_fields = col_cfg['csv_fields']
            operation = col_cfg['operation']
            
            if operation == 'sum':
                # Sum multiple CSV fields
                values = []
                for field in csv_fields:
                    if field in row_data.index:
                        # Try to convert to float, default to 0 if fails
                        try:
                            val = float(row_data[field]) if pd.notna(row_data[field]) else 0.0
                        except (ValueError, TypeError):
                            val = 0.0
                        values.append(val)
                    else:
                        values.append(0.0)
                value = sum(values)
            else:
                # Unknown operation, fallback to empty
                value = ''
        
        elif 'csv_field' in col_cfg:
            # Single field mapping (existing behavior)
            csv_field = col_cfg['csv_field']
            value = str(row_data.get(csv_field, '')) if csv_field in row_data.index else ''
        
        else:
            # No valid field mapping
            value = ''
        
        row_list[offset] = value
    
    return row_list

def upload_reservations(client, config, spreadsheet_id, csv_file, hard_replace=False):
    """Upload processed reservations using dynamic column mapping from config.
    
    Returns:
        str: URL to the Google Sheet
    """
    
    print_header("📊 UPLOAD SUMMARY", "=")
    
    # Get language setting
    language = config.get('_language', 'en')
    
    # Read CSV
    df = pd.read_csv(csv_file)
    print_step("📂", f"Loaded {len(df)} reservations from CSV")
    
    # Convert dates
    df['Entrada'] = pd.to_datetime(df['Entrada']).dt.strftime('%Y-%m-%d')
    df['Salida'] = pd.to_datetime(df['Salida']).dt.strftime('%Y-%m-%d')
    
    # Detect months
    target_tabs, month_names = detect_months_from_csv(csv_file)
    month_display_names = [get_month_name_for_display(m, language) for m in month_names]
    print_step("📅", f"Target months: {', '.join(month_display_names)}")
    
    # Open spreadsheet
    print_step("🔗", "Connecting to Google Sheets...")
    spreadsheet = client.open_by_key(spreadsheet_id)
    print_success(f"Connected: '{spreadsheet.title}'")
    
    # Build sheet URL
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
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
        tab_config = config['tabs'][tab_key]
        tab_name = get_tab_name(config, tab_key)
        
        if tab_name not in available_tabs:
            print_info(f"⚠️  Tab '{tab_name}' not found in spreadsheet, skipping clear", indent=1)
            continue

        try:
            ws = get_worksheet_fuzzy(spreadsheet, tab_name)
            # Use physical_columns from config for dynamic clearing
            num_cols = tab_config.get('physical_columns', len(tab_config['columns']))
            clear_exact_range(ws, tab_config['start_range'], num_cols, 15)
            print_info(f"{tab_name}: Cleared {num_cols} columns", indent=1)
            cleared_count += 1
        except gspread.exceptions.WorksheetNotFound:
            print_info(f"⚠️  Tab '{tab_name}' not found in spreadsheet, skipping clear", indent=1)
            continue
    
    print_success(f"Cleared {cleared_count} tabs")
    
    # Upload phase
    print_header("📤 UPLOAD PHASE", "-")
    
    df['month_name'] = pd.to_datetime(df['Entrada']).dt.strftime('%B').str.lower()
    df = df.replace([float('inf'), float('-inf')], pd.NA).fillna('')
    
    total_uploaded = 0
    
    for tab_key in target_tabs:
        tab_config = config['tabs'][tab_key]
        tab_name = get_tab_name(config, tab_key)
        
        if tab_name not in available_tabs:
            print_info(f"⚠️  Tab '{tab_name}' not found in spreadsheet, skipping upload", indent=1)
            continue

        month_data = df[df['month_name'] == tab_key.split('_')[0]]
        
        # Get month name in the configured language
        month_key = tab_key.split('_')[0]
        month_display = get_month_name_for_display(month_key, language)
        
        try:
            worksheet = get_worksheet_fuzzy(spreadsheet, tab_name)
        except gspread.exceptions.WorksheetNotFound:
            print_info(f"⚠️  Tab '{tab_name}' not found in spreadsheet, skipping upload", indent=1)
            continue

        # Update B2 with month name in configured language
        worksheet.update(values=[[month_display]], range_name='B2', value_input_option='USER_ENTERED')
        
        if len(month_data) > 0:
            columns = tab_config['columns']
            column_mapping = tab_config.get('column_mapping', {})
            
            # If no column_mapping provided, fall back to simple ordered mapping
            if not column_mapping:
                print_info(f"⚠️  No column_mapping for {tab_key}, using simple mapping", indent=1)
                processed_rows = []
                for _, row in month_data.iterrows():
                    row_list = [str(row.get(col, '')) for col in columns]
                    processed_rows.append(row_list)
            else:
                # Use dynamic mapping
                processed_rows = []
                for _, row in month_data.iterrows():
                    row_list = build_row_from_mapping(row, column_mapping, columns)
                    processed_rows.append(row_list)
            
            start_cell = tab_config['start_range']
            worksheet.update(values=processed_rows, range_name=start_cell, value_input_option='USER_ENTERED')
            print_step("✓", f"{month_display}: {len(processed_rows)} reservations", indent=1)
            total_uploaded += len(processed_rows)
    
    print_header("🎉 COMPLETE", "=")
    print_step("📊", f"Total uploaded: {total_uploaded} reservations")
    print_step("📅", f"Months updated: {len(target_tabs)}")
    print_step("🗂️", f"Spreadsheet: {spreadsheet.title}")
    print_step("🔗", f"View at: {sheet_url}")
    
    return sheet_url

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
    
    sheet_url = upload_reservations(client, config, config['spreadsheet_id'], args.csv, args.hard_replace)

if __name__ == "__main__":
    main()



