#!/usr/bin/env python3
"""
Create invoices from apartment reservation data.

Generates Google Sheets invoices with separate numbering for test/production.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

PROJECT_ROOT = Path(__file__).parent.parent


def load_invoice_config():
    """Load invoice configuration."""
    config_path = PROJECT_ROOT / "config/invoice_config.json"
    with open(config_path, 'r') as f:
        return json.load(f)


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

    existing = list(invoice_dir.glob(pattern))
    numbers = []
    for f in existing:
        # stem: MED_0001 or TEST_MED_0001
        m = re.search(r'_(\d+)$', f.stem)
        if m:
            numbers.append(int(m.group(1)))

    next_num = max(numbers, default=0) + 1
    base = f"{invoice_code}_{next_num:04d}"
    return f"TEST_{base}" if test else base


def get_gspread_client():
    """Authenticate and return gspread client."""
    creds_path = PROJECT_ROOT / "credentials/service_account.json"
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    return gspread.authorize(creds)


def copy_template_invoice(client, template_id, invoice_number):
    """Copy invoice template and rename it.
    
    Args:
        client: gspread client
        template_id: Template spreadsheet ID
        invoice_number: Invoice number (e.g., 'MED_0001' or 'TEST_MED_0001')
    
    Returns:
        gspread.Spreadsheet: New invoice sheet
    """
    new_title = f"Invoice {invoice_number}"
    new_sheet = client.copy(template_id, title=new_title)
    return new_sheet


def populate_invoice_data(sheet, reservation_data, apartment_info):
    """Populate invoice with reservation data.
    
    Args:
        sheet: gspread.Spreadsheet
        reservation_data: dict with reservation information
        apartment_info: dict with apartment information
    """
    # Get first worksheet
    worksheet = sheet.get_worksheet(0)
    
    # TODO: Implement data population based on your invoice template
    # This is a placeholder - customize based on your template structure
    # Example:
    # worksheet.update('A1', apartment_info['name'])
    # worksheet.update('A2', reservation_data['guest_name'])
    # etc.
    
    print(f"  Populated invoice with reservation data")


def share_invoice(sheet, emails):
    """Share invoice with specified emails.
    
    Args:
        sheet: gspread.Spreadsheet
        emails: list of email addresses
    """
    for email in emails:
        sheet.share(email, perm_type='user', role='reader')
        print(f"  Shared with: {email}")


def save_invoice_metadata(apartment, invoice_number, metadata):
    """Save invoice metadata to JSON file.
    
    Args:
        apartment: Apartment name
        invoice_number: Invoice number
        metadata: dict with invoice metadata
    """
    invoice_dir = PROJECT_ROOT / "invoices" / apartment
    invoice_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_file = invoice_dir / f"{invoice_number}.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved metadata: {metadata_file}")


def create_invoice(apartment, months, year, additional_emails=None, test=False):
    """Create invoice for apartment reservation.
    
    Args:
        apartment: Apartment name
        months: List of month keys (e.g., ['january', 'february'])
        year: Year
        additional_emails: Additional emails to share with
        test: If True, use test config and TEST_ invoice numbering
    """
    print(f"\nCreating {'TEST' if test else 'PRODUCTION'} invoice for {apartment} ({year})...")
    
    # Load configs
    invoice_config = load_invoice_config()
    apartment_config = load_apartment_config(apartment, year, test=test)
    
    # Get apartment info
    apartment_info = invoice_config['apartments'].get(apartment)
    if not apartment_info:
        raise ValueError(f"Apartment '{apartment}' not found in invoice config")
    
    # Generate invoice number
    invoice_number = get_next_invoice_number(
        apartment,
        apartment_info['invoice_code'],
        test=test,
    )
    print(f"  Invoice number: {invoice_number}")
    
    # Get Google Sheets client
    client = get_gspread_client()
    
    # Copy template
    template_id = invoice_config['template_id']
    print(f"  Copying template...")
    new_sheet = copy_template_invoice(client, template_id, invoice_number)
    print(f"  Created sheet: {new_sheet.url}")
    
    # Gather reservation data for specified months
    reservation_data = {
        'months': months,
        'apartment': apartment,
        'year': year,
        # TODO: Extract actual reservation data from apartment_config
    }
    
    # Populate invoice
    print(f"  Populating invoice...")
    populate_invoice_data(new_sheet, reservation_data, apartment_info)
    
    # Share invoice
    share_emails = [apartment_info.get('owner_email', '')]
    if additional_emails:
        share_emails.extend(additional_emails)
    share_emails = [e for e in share_emails if e]  # Filter empty emails
    
    if share_emails:
        print(f"  Sharing invoice...")
        share_invoice(new_sheet, share_emails)
    
    # Save metadata
    metadata = {
        'invoice_number': invoice_number,
        'apartment': apartment,
        'year': year,
        'months': months,
        'test_mode': test,
        'created_at': datetime.now().isoformat(),
        'sheet_id': new_sheet.id,
        'sheet_url': new_sheet.url,
    }
    save_invoice_metadata(apartment, invoice_number, metadata)
    
    print(f"\n✅ Invoice created successfully: {invoice_number}")
    print(f"   URL: {new_sheet.url}")
    
    return invoice_number, new_sheet.url


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

    create_invoice(
        args.apartment,
        months,
        args.year,
        additional_emails,
        test=args.test,
    )
