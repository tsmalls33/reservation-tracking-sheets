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
    """Create DataFrame from extracted month data."""
    df = pd.DataFrame(month_data_list)
    
    # Calculate totals
    total_rent = df['rent'].sum()
    total_profit = df['profit'].sum()
    total_fee = df['fee_amount'].sum()
    
    # Add totals row
    totals = {
        'month': 'TOTAL',
        'rent': total_rent,
        'profit': total_profit,
        'fee_percent': '',
        'fee_amount': total_fee
    }
    
    df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
    
    # Return df and calculated totals separately
    return df, {'rent': total_rent, 'profit': total_profit, 'fee': total_fee}

def copy_template_invoice(client, template_id, invoice_number, owner_email=None):
    """Use the shared template directly and just rename it.
    
    Since service accounts have no storage, we'll work with a single
    pre-shared template that gets reused.
    """
    # Open the shared template
    spreadsheet = client.open_by_key(template_id)
    
    # Rename it
    spreadsheet.update_title(f"Invoice {invoice_number}")
    
    # Share with owner
    if owner_email:
        try:
            spreadsheet.share(owner_email, perm_type='user', role='writer', notify=False)
        except Exception as e:
            print(f"   ⚠️  Could not share with {owner_email}: {e}")
    
    return spreadsheet

def generate_pdf_export_link(spreadsheet_id, sheet_name="Sheet1"):
    """Generate a direct link to export the spreadsheet as PDF.
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to export (default: first sheet)
        
    Returns:
        str: Direct URL to download PDF
    """
    # Google Sheets PDF export URL format
    base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
    
    params = {
        'format': 'pdf',
        'size': 'A4',  # Paper size
        'portrait': 'true',  # Orientation
        'fitw': 'true',  # Fit to width
        'gridlines': 'false',  # Hide gridlines
        'printtitle': 'false',  # Don't print title
        'sheetnames': 'false',  # Don't print sheet names
        'pagenum': 'false',  # Don't print page numbers
        'attachment': 'false',  # Display in browser instead of download
        'gid': '0'  # First sheet (sheet ID, not name)
    }
    
    return f"{base_url}?{urlencode(params)}"

def cleanup_template_before_populate(client, spreadsheet, invoice_config):
    """Clear any existing data from template before populating.
    
    This ensures the template is clean before we add new invoice data.
    
    Args:
        client: gspread client
        spreadsheet: The spreadsheet object
        invoice_config: Invoice configuration
    """
    worksheet = spreadsheet.sheet1
    mapping = invoice_config['invoice_mapping']
    
    # Clear header fields
    header_ranges = [
        mapping['client_name'],
        mapping['property_name'],
        mapping['invoice_number']
    ]
    
    for range_name in header_ranges:
        worksheet.update(values=[['']], range_name=range_name)
    
    # Clear total cells if they exist in config
    total_cells = []
    if 'total_rent_cell' in mapping:
        total_cells.append(mapping['total_rent_cell'])
    if 'total_profit_cell' in mapping:
        total_cells.append(mapping['total_profit_cell'])
    if 'total_fee_cell' in mapping:
        total_cells.append(mapping['total_fee_cell'])
    
    for cell in total_cells:
        worksheet.update(values=[['']], range_name=cell)
    
    # Clear table data area (use a reasonable range)
    # Assuming max 20 rows of data (adjust if needed)
    table_start_row = mapping['table_start_row']
    table_start_col = mapping['table_start_col']
    
    # Clear up to 20 rows, 5 columns (month, rent, profit, fee%, fee amount)
    num_rows = 20
    num_cols = 5
    
    end_col_num = ord(table_start_col) + num_cols - 1
    end_col = chr(end_col_num)
    end_row = table_start_row + num_rows - 1
    
    range_name = f"{table_start_col}{table_start_row}:{end_col}{end_row}"
    empty_data = [[''] * num_cols for _ in range(num_rows)]
    worksheet.update(values=empty_data, range_name=range_name)

def populate_invoice(client, spreadsheet, invoice_config, apartment_info, invoice_number, df, totals):
    """Populate invoice with data.
    
    Args:
        client: gspread client
        spreadsheet: Spreadsheet object
        invoice_config: Invoice configuration
        apartment_info: Apartment info from config
        invoice_number: Invoice number
        df: DataFrame with month data
        totals: Dict with total values {'rent': X, 'profit': Y, 'fee': Z}
    """
    worksheet = spreadsheet.sheet1  # Assume first sheet
    
    mapping = invoice_config['invoice_mapping']
    
    # Write header info
    worksheet.update(values=[[apartment_info['client_name']]], range_name=mapping['client_name'])
    worksheet.update(values=[[apartment_info['property_name']]], range_name=mapping['property_name'])
    worksheet.update(values=[[invoice_number]], range_name=mapping['invoice_number'])
    
    # Write table data
    table_start_row = mapping['table_start_row']
    table_start_col = mapping['table_start_col']
    
    # Prepare table data (all rows including TOTAL)
    table_data = df.values.tolist()
    
    # Calculate range
    num_cols = len(df.columns)
    end_col_num = ord(table_start_col) + num_cols - 1
    end_col = chr(end_col_num)
    end_row = table_start_row + len(df) - 1
    
    range_name = f"{table_start_col}{table_start_row}:{end_col}{end_row}"
    worksheet.update(values=table_data, range_name=range_name)
    
    # Write total cells separately as plain floats (if defined in mapping)
    # This preserves the cell's number formatting
    if 'total_rent_cell' in mapping:
        worksheet.update(values=[[totals['rent']]], range_name=mapping['total_rent_cell'])
        print(f"   → Total Rent ({mapping['total_rent_cell']}): {totals['rent']:.2f}")
    
    if 'total_profit_cell' in mapping:
        worksheet.update(values=[[totals['profit']]], range_name=mapping['total_profit_cell'])
        print(f"   → Total Profit ({mapping['total_profit_cell']}): {totals['profit']:.2f}")
    
    if 'total_fee_cell' in mapping:
        worksheet.update(values=[[totals['fee']]], range_name=mapping['total_fee_cell'])
        print(f"   → Total Fee ({mapping['total_fee_cell']}): {totals['fee']:.2f}")

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
    
    if not owner_email or owner_email == 'YOUR_EMAIL@example.com':
        print_step("⚠️", "Warning: owner_email not configured in config/invoices.json")
        print("   Update the 'owner_email' field to automatically share invoices with yourself.")
        owner_email = None
    
    # Authenticate
    print_step("🔐", "Authenticating...")
    client = authenticate_sheets()
    
    # Generate invoice number
    invoice_number = get_next_invoice_number(apartment, apartment_info['invoice_code'], test=test)
    print_step("🔢", f"Invoice number: {invoice_number}")
    
    # Extract data from each month
    print_step("📅", f"Extracting data for {len(months)} month(s)...")
    month_data_list = []
    for month in months:
        print(f"   → {month.capitalize()}...")
        data = extract_month_data(client, apartment_config, invoice_config, month, year)
        month_data_list.append(data)
        # Small delay between months to avoid rate limits
        time.sleep(0.5)
    
    # Create DataFrame and calculate totals
    df, totals = create_invoice_dataframe(month_data_list)
    print_step("✅", "Data aggregated")
    print(f"   Total Rent: {totals['rent']:.2f}")
    print(f"   Total Profit: {totals['profit']:.2f}")
    print(f"   Total Fee: {totals['fee']:.2f}")
    
    # Copy template
    print_step("📋", "Copying invoice template...")
    template_id = invoice_config['template_sheet_id']
    new_invoice = copy_template_invoice(client, template_id, invoice_number, owner_email)
    
    # Clean template BEFORE populating (ensures blank slate)
    print_step("🧹", "Preparing clean template...")
    try:
        cleanup_template_before_populate(client, new_invoice, invoice_config)
        print_step("✅", "Template cleaned")
    except Exception as e:
        print_step("⚠️", f"Could not clean template: {e}")
    
    # Populate invoice
    print_step("✏️", "Populating invoice...")
    populate_invoice(client, new_invoice, invoice_config, apartment_info, invoice_number, df, totals)
    
    # Generate PDF export link (after populating, so it contains data)
    print_step("📄", "Generating PDF export link...")
    pdf_link = generate_pdf_export_link(new_invoice.id)
    print_step("✅", f"PDF link ready")
    
    # Prepare email list (always include owner, plus any additional)
    emails_to_share = []
    if owner_email:
        emails_to_share.append(owner_email)
    if additional_emails:
        emails_to_share.extend(additional_emails)
    
    # Save metadata
    metadata = {
        'invoice_number': invoice_number,
        'apartment': apartment,
        'months': months,
        'year': year,
        'test_mode': test,
        'created_at': datetime.now().isoformat(),
        'spreadsheet_id': new_invoice.id,
        'spreadsheet_url': new_invoice.url,
        'pdf_export_link': pdf_link,
        'shared_with': emails_to_share,
        'totals': {
            'rent': totals['rent'],
            'profit': totals['profit'],
            'fee': totals['fee']
        }
    }
    save_invoice_metadata(apartment, invoice_number, metadata)
    
    print_header("✅ INVOICE CREATED", "=")
    print(f"Invoice Number: {invoice_number}")
    print(f"\n📄 PDF Export Link (open to download):")
    print(f"   {pdf_link}")
    print(f"\n🔗 View/Edit Spreadsheet:")
    print(f"   {new_invoice.url}")
    if emails_to_share:
        print(f"\n📤 Accessible by: {', '.join(emails_to_share)}")
    print(f"\nℹ️  Spreadsheet remains populated with invoice data")
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
