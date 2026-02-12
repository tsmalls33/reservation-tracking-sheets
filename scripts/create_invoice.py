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

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = PROJECT_ROOT / 'credentials/service_account.json'
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    return gspread.authorize(creds)

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
    data = {}
    
    for key, cell in source_cells.items():
        value = worksheet.acell(cell).value
        # Clean and convert to float if numeric
        try:
            # Remove currency symbols and convert
            clean_value = value.replace('€', '').replace(',', '.').strip() if value else '0'
            data[key] = float(clean_value)
        except:
            data[key] = value
    
    return {
        'month': MONTH_NAMES[month_key][language],
        'rent': data.get('renta_mensual', 0),
        'profit': data.get('ganancia_mensual', 0),
        'fee_percent': data.get('percentage', 0),
        'fee_amount': data.get('comision_devomart', 0)
    }

def create_invoice_dataframe(month_data_list):
    """Create DataFrame from extracted month data."""
    df = pd.DataFrame(month_data_list)
    
    # Add totals row
    totals = {
        'month': 'TOTAL',
        'rent': df['rent'].sum(),
        'profit': df['profit'].sum(),
        'fee_percent': '',
        'fee_amount': df['fee_amount'].sum()
    }
    
    df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
    return df

def copy_template_invoice(client, template_id, invoice_number):
    """Copy invoice template and return new spreadsheet."""
    new_sheet = client.copy(template_id, title=f"Invoice {invoice_number}")
    return new_sheet

def populate_invoice(client, spreadsheet, invoice_config, apartment_info, invoice_number, df):
    """Populate invoice with data."""
    worksheet = spreadsheet.sheet1  # Assume first sheet
    
    mapping = invoice_config['invoice_mapping']
    
    # Write header info
    worksheet.update(values=[[apartment_info['client_name']]], range_name=mapping['client_name'])
    worksheet.update(values=[[apartment_info['property_name']]], range_name=mapping['property_name'])
    worksheet.update(values=[[invoice_number]], range_name=mapping['invoice_number'])
    
    # Write table data (excluding TOTAL row for now)
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
    
    return spreadsheet

def share_invoice(client, spreadsheet_id, email_addresses):
    """Share invoice with one or more email addresses.
    
    Args:
        client: gspread client
        spreadsheet_id: ID of the spreadsheet to share
        email_addresses: List of email addresses to share with
    """
    from googleapiclient.discovery import build
    
    creds_path = PROJECT_ROOT / 'credentials/service_account.json'
    creds = Credentials.from_service_account_file(
        str(creds_path),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    drive_service = build('drive', 'v3', credentials=creds)
    
    for email in email_addresses:
        try:
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email
                },
                sendNotificationEmail=False
            ).execute()
            print_step("✅", f"Shared with {email}")
        except Exception as e:
            print_step("⚠️", f"Failed to share with {email}: {e}")

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
    
    # Create DataFrame
    df = create_invoice_dataframe(month_data_list)
    print_step("✅", "Data aggregated")
    
    # Copy template
    print_step("📋", "Copying invoice template...")
    template_id = invoice_config['template_sheet_id']
    new_invoice = copy_template_invoice(client, template_id, invoice_number)
    
    # Populate invoice
    print_step("✏️", "Populating invoice...")
    populate_invoice(client, new_invoice, invoice_config, apartment_info, invoice_number, df)
    
    # Prepare email list (always include owner, plus any additional)
    emails_to_share = []
    if owner_email and owner_email != 'YOUR_EMAIL@example.com':
        emails_to_share.append(owner_email)
    if additional_emails:
        emails_to_share.extend(additional_emails)
    
    # Share with all emails
    if emails_to_share:
        print_step("📧", "Sharing invoice...")
        share_invoice(client, new_invoice.id, emails_to_share)
    
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
        'shared_with': emails_to_share
    }
    save_invoice_metadata(apartment, invoice_number, metadata)
    
    print_header("✅ INVOICE CREATED", "=")
    print(f"Invoice Number: {invoice_number}")
    print(f"\n🔗 Open in Google Sheets:")
    print(f"   {new_invoice.url}")
    print(f"\n🆔 Spreadsheet ID: {new_invoice.id}")
    if emails_to_share:
        print(f"\n📤 Shared with: {', '.join(emails_to_share)}")
    print()
    
    return invoice_number, new_invoice.url

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
