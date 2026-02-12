#!/usr/bin/env python3
"""
Invoice Creation Script - Generate invoices from apartment reservation data
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import sys
import re
from pathlib import Path
from datetime import datetime
import time
from urllib.parse import urlencode

PROJECT_ROOT = Path("/Users/thomas/dev/reservation-tracking-sheets")

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
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}")

def print_step(emoji, message):
    print(f"{emoji} {message}")

def get_credentials():
    """Get credentials for Google APIs."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = PROJECT_ROOT / 'credentials/service_account.json'
    return Credentials.from_service_account_file(str(creds_path), scopes=scope)

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    creds = get_credentials()
    return gspread.authorize(creds)

def parse_financial_value(value):
    """Parse a financial value from string to float.
    
    Handles European format (1.234,56€) and US format (1,234.56$)
    Also handles percentages (15%).
    
    Args:
        value: String value from spreadsheet
        
    Returns:
        float: Parsed numeric value, or 0.0 if parsing fails
    """
    if not value or (isinstance(value, str) and value.strip() == ''):
        return 0.0
    
    # Convert to string if needed
    value_str = str(value).strip()
    
    try:
        # Handle percentages
        if '%' in value_str:
            # Remove % and convert (15% -> 15.0)
            clean_value = value_str.replace('%', '').strip()
            # Remove any spaces
            clean_value = clean_value.replace(' ', '')
            return float(clean_value)
        
        # Remove currency symbols
        clean_value = value_str
        for symbol in ['€', '$', '£', '¥']:
            clean_value = clean_value.replace(symbol, '')
        
        # Remove spaces
        clean_value = clean_value.strip().replace(' ', '')
        
        # Detect format based on which comes last: comma or dot
        # European: 1.234,56 (comma is decimal separator)
        # US: 1,234.56 (dot is decimal separator)
        
        last_comma = clean_value.rfind(',')
        last_dot = clean_value.rfind('.')
        
        if last_comma > last_dot:
            # European format: comma is decimal separator
            # Remove dots (thousands separator) and replace comma with dot
            clean_value = clean_value.replace('.', '').replace(',', '.')
        else:
            # US format: dot is decimal separator
            # Just remove commas (thousands separator)
            clean_value = clean_value.replace(',', '')
        
        return float(clean_value)
        
    except (ValueError, AttributeError) as e:
        print(f"   ⚠️  Warning: Could not parse '{value}', using 0.0")
        return 0.0

def get_next_invoice_number(apartment, invoice_code, test=False):
    """Generate next invoice number for apartment.
    
    Args:
        apartment: Apartment name
        invoice_code: Invoice code (e.g., 'MED', 'SANT')
        test: If True, use TEST_ prefix and separate numbering
    
    Returns:
        str: Next invoice number (e.g., 'MED_0001' or 'TEST_MED_0001')
    """
    invoice_dir = PROJECT_ROOT / "invoices" / apartment
    invoice_dir.mkdir(parents=True, exist_ok=True)
    
    if test:
        # TEST_MED_0001.json, TEST_MED_0002.json, ...
        pattern = f"TEST_{invoice_code}_*.json"
    else:
        # MED_0001.json, MED_0002.json, ...
        pattern = f"{invoice_code}_*.json"
    
    # Find existing invoice metadata files
    existing = list(invoice_dir.glob(pattern))
    
    # Extract numbers
    numbers = []
    for f in existing:
        # stem: MED_0001 or TEST_MED_0001
        m = re.search(r'_(\d+)$', f.stem)
        if m:
            numbers.append(int(m.group(1)))
    
    next_num = max(numbers, default=0) + 1
    base = f"{invoice_code}_{next_num:04d}"
    return f"TEST_{base}" if test else base

def load_apartment_config(apartment, year, test=False):
    """Load apartment configuration.
    
    Args:
        apartment: Apartment name
        year: Year
        test: If True, load {apartment}_{year}_test.json instead
    
    Returns:
        dict: Apartment configuration
    """
    suffix = '_test' if test else ''
    config_path = PROJECT_ROOT / f"config/{apartment}_{year}{suffix}.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def load_invoice_config():
    """Load invoice configuration."""
    config_path = PROJECT_ROOT / "config/invoices.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def get_month_tab_name(month_key, language='es'):
    """Get the localized month name for the tab."""
    return MONTH_NAMES[month_key][language]

def extract_month_data(client, apartment_config, invoice_config, month_key, year):
    """Extract financial data from a specific month tab."""
    language = apartment_config.get('language', 'es')
    tab_name = get_month_tab_name(month_key, language)
    
    # Open apartment spreadsheet
    spreadsheet = client.open_by_key(apartment_config['spreadsheet_id'])
    
    # Find worksheet
    worksheet = None
    for ws in spreadsheet.worksheets():
        if ws.title.strip() == tab_name:
            worksheet = ws
            break
    
    if not worksheet:
        raise ValueError(f"Tab '{tab_name}' not found in spreadsheet")
    
    # Extract source cells
    source_cells = invoice_config['source_cells']
    
    # Batch read all cells at once to reduce API calls
    cell_list = list(source_cells.values())
    
    try:
        # Get all cell values in one API call using batch_get
        cell_values = worksheet.batch_get(cell_list)
        
        # Map cell references to values
        data = {}
        for i, (key, cell) in enumerate(source_cells.items()):
            try:
                value = cell_values[i][0][0] if cell_values[i] and cell_values[i][0] else ''
            except (IndexError, KeyError):
                value = ''
            
            # Parse the value
            data[key] = parse_financial_value(value)
    
    except Exception as e:
        # Fallback to individual cell reads if batch fails
        print(f"   ⚠️  Batch read failed, falling back to individual reads: {e}")
        data = {}
        for key, cell in source_cells.items():
            value = worksheet.acell(cell).value
            data[key] = parse_financial_value(value)
            time.sleep(0.1)  # Small delay to avoid rate limits
    
    return {
        'month': MONTH_NAMES[month_key][language],
        'rent': data.get('renta_mensual', 0.0),
        'profit': data.get('ganancia_mensual', 0.0),
        'fee_percent': data.get('percentage', 0.0),
        'fee_amount': data.get('comision_devomart', 0.0)
    }

def create_invoice_dataframe(month_data_list):
    """Create DataFrame from extracted month data.
    
    Returns DataFrame with only month rows (no TOTAL row).
    The commission total is calculated and returned separately.
    
    Returns:
        tuple: (DataFrame with month rows only, commission total)
    """
    df = pd.DataFrame(month_data_list)
    
    # Calculate total commission
    commission_total = df['fee_amount'].sum()
    
    # Return DataFrame without TOTAL row, and the commission total separately
    return df, commission_total

def generate_pdf_export_link(spreadsheet_id):
    """Generate a direct link to export the spreadsheet as PDF.
    
    Uses Google Sheets export endpoint with URL parameters for PDF generation.
    This creates a direct download link that works for authenticated users.
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        
    Returns:
        str: Direct PDF download URL
    """
    # Google Sheets PDF export URL format
    base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
    
    # URL parameters for PDF export
    params = {
        'format': 'pdf',           # Export format
        'size': 'A4',              # Paper size (A4)
        'portrait': 'true',        # Orientation (portrait)
        'fitw': 'true',            # Fit to width
        'gridlines': 'false',      # Hide gridlines
        'printtitle': 'false',     # Don't print title
        'sheetnames': 'false',     # Don't print sheet names
        'pagenum': 'false',        # Don't print page numbers
        'attachment': 'true',      # Force download (true) vs display in browser (false)
        'gid': '0'                 # Sheet ID (0 = first sheet)
    }
    
    return f"{base_url}?{urlencode(params)}"

def cleanup_template_before_populate(worksheet, invoice_config):
    """Clear ALL cells that will be touched during invoice population.
    
    This clears cell content while preserving formatting (borders, colors, styles).
    Always clears 12 rows for potential 12 months of data (no TOTAL row).
    
    Args:
        worksheet: The worksheet object
        invoice_config: Invoice configuration
    """
    mapping = invoice_config['invoice_mapping']
    
    # Collect all ranges to clear (preserves formatting)
    ranges_to_clear = [
        mapping['invoice_number'],      # B16
        mapping['invoice_date'],        # B14
        mapping['client_name'],         # E7
        mapping['property_name'],       # B22
    ]
    
    # Add optional client detail cells if present in mapping
    optional_cells = [
        'client_address',   # E8
        'client_zip_code',  # E9
        'client_city',      # E10
        'client_id'         # E11
    ]
    
    for cell_key in optional_cells:
        if cell_key in mapping and mapping[cell_key]:
            ranges_to_clear.append(mapping[cell_key])
    
    # Add commission total cell
    if 'commission_total_cell' in mapping:
        ranges_to_clear.append(mapping['commission_total_cell'])  # H36
    
    # Add the table area - ALWAYS 12 rows for months (no TOTAL row)
    table_start_row = mapping['table_start_row']  # 26
    table_start_col = mapping['table_start_col']  # A
    
    # DataFrame has 5 columns: month, rent, profit, fee_percent, fee_amount
    num_cols = 5
    num_rows = 12  # Always clear for 12 months (no TOTAL row)
    
    # Calculate end column (A + 5 columns = E)
    end_col_num = ord(table_start_col) + num_cols - 1
    end_col = chr(end_col_num)
    end_row = table_start_row + num_rows - 1
    
    table_range = f"{table_start_col}{table_start_row}:{end_col}{end_row}"
    ranges_to_clear.append(table_range)
    
    # Use batch_clear to clear content while preserving formatting
    worksheet.batch_clear(ranges_to_clear)
    
    print(f"   → Cleared {len(ranges_to_clear) - 1} individual cells")
    print(f"   → Cleared table range {table_range} ({num_rows} rows x {num_cols} cols)")
    print(f"   → Formatting preserved")

def populate_invoice(client, spreadsheet, invoice_config, apartment_info, invoice_number, invoice_date, df, commission_total):
    """Populate invoice with data.
    
    Args:
        client: gspread client
        spreadsheet: Spreadsheet object
        invoice_config: Invoice configuration
        apartment_info: Apartment info from config
        invoice_number: Invoice number
        invoice_date: Invoice creation date (formatted string)
        df: DataFrame with month data (no TOTAL row)
        commission_total: Total commission amount
    """
    worksheet = spreadsheet.sheet1  # Assume first sheet
    
    mapping = invoice_config['invoice_mapping']
    
    # Write header info
    worksheet.update(values=[[invoice_number]], range_name=mapping['invoice_number'])
    worksheet.update(values=[[invoice_date]], range_name=mapping['invoice_date'])
    worksheet.update(values=[[apartment_info['client_name']]], range_name=mapping['client_name'])
    worksheet.update(values=[[apartment_info['property_name']]], range_name=mapping['property_name'])
    
    # Write optional client details if present
    if 'client_address' in apartment_info and 'client_address' in mapping:
        worksheet.update(values=[[apartment_info['client_address']]], range_name=mapping['client_address'])
    
    if 'client_zip_code' in apartment_info and 'client_zip_code' in mapping:
        worksheet.update(values=[[apartment_info['client_zip_code']]], range_name=mapping['client_zip_code'])
    
    if 'client_city' in apartment_info and 'client_city' in mapping:
        worksheet.update(values=[[apartment_info['client_city']]], range_name=mapping['client_city'])
    
    if 'client_id' in apartment_info and 'client_id' in mapping:
        worksheet.update(values=[[apartment_info['client_id']]], range_name=mapping['client_id'])
    
    # Write table data (only month rows, no TOTAL row)
    table_start_row = mapping['table_start_row']
    table_start_col = mapping['table_start_col']
    
    # Prepare table data - convert DataFrame to list of lists
    table_data = df.values.tolist()
    
    # Calculate range
    num_cols = len(df.columns)
    end_col_num = ord(table_start_col) + num_cols - 1
    end_col = chr(end_col_num)
    end_row = table_start_row + len(df) - 1
    
    range_name = f"{table_start_col}{table_start_row}:{end_col}{end_row}"
    
    # Use value_input_option='USER_ENTERED' to let Sheets interpret the data types
    worksheet.update(values=table_data, range_name=range_name, value_input_option='USER_ENTERED')
    
    # Write commission total separately (H36)
    if 'commission_total_cell' in mapping:
        worksheet.update(values=[[commission_total]], range_name=mapping['commission_total_cell'])
        print(f"   → Commission Total ({mapping['commission_total_cell']}): {commission_total:.2f}")

def save_invoice_metadata(apartment, invoice_number, invoice_data):
    """Save invoice metadata locally."""
    invoice_dir = PROJECT_ROOT / "invoices" / apartment
    invoice_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_file = invoice_dir / f"{invoice_number}.json"
    with open(metadata_file, 'w') as f:
        json.dump(invoice_data, f, indent=2)

def create_invoice(apartment, months, year, additional_emails=None, test=False):
    """Main invoice creation function.
    
    Args:
        apartment: Apartment name
        months: List of month keys
        year: Year
        additional_emails: Optional list of additional emails to share with
        test: If True, use test config and TEST_ invoice numbering
    """
    mode_label = "TEST" if test else "PRODUCTION"
    print_header(f"📄 INVOICE CREATION ({mode_label})")
    
    # Load configs
    print_step("📂", "Loading configurations...")
    invoice_config = load_invoice_config()
    apartment_config = load_apartment_config(apartment, year, test=test)
    
    if apartment not in invoice_config['apartments']:
        raise ValueError(f"Apartment '{apartment}' not configured in invoices.json")
    
    apartment_info = invoice_config['apartments'][apartment]
    owner_email = invoice_config.get('owner_email')
    template_id = invoice_config['template_sheet_id']
    
    if not owner_email or owner_email == 'YOUR_EMAIL@example.com':
        print_step("⚠️", "Warning: owner_email not configured in config/invoices.json")
        print("   Update the 'owner_email' field to automatically share invoices with yourself.")
        owner_email = None
    
    # Authenticate
    print_step("🔐", "Authenticating...")
    client = authenticate_sheets()
    
    # Generate invoice number and date
    invoice_number = get_next_invoice_number(apartment, apartment_info['invoice_code'], test=test)
    invoice_date = datetime.now().strftime('%d/%m/%Y')  # European date format
    
    print_step("🔢", f"Invoice number: {invoice_number}")
    print_step("📅", f"Invoice date: {invoice_date}")
    
    # Extract data from each month
    print_step("📅", f"Extracting data for {len(months)} month(s)...")
    month_data_list = []
    for month in months:
        print(f"   → {month.capitalize()}...")
        data = extract_month_data(client, apartment_config, invoice_config, month, year)
        month_data_list.append(data)
        # Small delay between months to avoid rate limits
        time.sleep(0.5)
    
    # Create DataFrame (no TOTAL row)
    df, commission_total = create_invoice_dataframe(month_data_list)
    print_step("✅", "Data aggregated")
    print(f"   Commission Total: {commission_total:.2f}")
    
    # Open the template spreadsheet
    print_step("📝", "Opening invoice template...")
    invoice_sheet = client.open_by_key(template_id)
    
    # Clean template (ensures blank slate, preserves formatting)
    print_step("🧹", "Cleaning template (preserving formatting)...")
    try:
        worksheet = invoice_sheet.sheet1
        cleanup_template_before_populate(worksheet, invoice_config)
        print_step("✅", "Template cleaned")
    except Exception as e:
        print_step("⚠️", f"Could not clean template: {e}")
    
    # Populate invoice
    print_step("✏️", "Populating invoice...")
    populate_invoice(client, invoice_sheet, invoice_config, apartment_info, invoice_number, invoice_date, df, commission_total)
    
    # Generate PDF export link
    print_step("📄", "Generating PDF export link...")
    pdf_link = generate_pdf_export_link(invoice_sheet.id)
    print_step("✅", "PDF export link ready")
    
    # Prepare email list (always include owner, plus any additional)
    emails_to_share = []
    if owner_email:
        emails_to_share.append(owner_email)
    if additional_emails:
        emails_to_share.extend(additional_emails)
    
    # Save metadata
    metadata = {
        'invoice_number': invoice_number,
        'invoice_date': invoice_date,
        'apartment': apartment,
        'months': months,
        'year': year,
        'test_mode': test,
        'created_at': datetime.now().isoformat(),
        'spreadsheet_id': invoice_sheet.id,
        'spreadsheet_url': invoice_sheet.url,
        'pdf_export_link': pdf_link,
        'shared_with': emails_to_share,
        'commission_total': commission_total
    }
    save_invoice_metadata(apartment, invoice_number, metadata)
    
    print_header("✅ INVOICE CREATED", "=")
    print(f"Invoice Number: {invoice_number}")
    print(f"Invoice Date: {invoice_date}")
    print(f"\n📄 PDF Export Link:")
    print(f"   {pdf_link}")
    print(f"\n🔗 View/Edit Spreadsheet:")
    print(f"   {invoice_sheet.url}")
    if emails_to_share:
        print(f"\n📤 Accessible by: {', '.join(emails_to_share)}")
    print(f"\nℹ️  Click the PDF link above to download invoice as PDF")
    print()
    
    return invoice_number, pdf_link

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create invoice from apartment data")
    parser.add_argument('--apartment', '-a', required=True)
    parser.add_argument('--months', '-m', required=True, help="Comma-separated month keys")
    parser.add_argument('--year', '-y', type=int, required=True)
    parser.add_argument('--email', '-e', help="Additional email(s) to share with (comma-separated)")
    parser.add_argument('--test', action='store_true',
                        help="Use test reservation config and test invoice numbering")
    
    args = parser.parse_args()
    months = [m.strip() for m in args.months.split(',')]
    
    additional_emails = None
    if args.email:
        additional_emails = [e.strip() for e in args.email.split(',')]
    
    create_invoice(args.apartment, months, args.year, additional_emails, test=args.test)
