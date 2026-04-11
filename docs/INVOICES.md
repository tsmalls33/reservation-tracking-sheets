# Invoice System

Generate professional invoices from reservation data with automatic calculations and PDF export.

## Overview

The invoice system:
- Extracts financial data from month tabs
- Calculates commission totals
- Populates invoice template
- Generates PDF export links
- Tracks invoice numbers per apartment

## Setup

### 1. Configure Invoice Settings

```bash
rez invoice config
```

Edits `config/invoices.json`:

```json
{
  "template_sheet_id": "YOUR_TEMPLATE_SPREADSHEET_ID",
  "owner_email": "your.email@example.com",
  "apartments": {
    "downtown-loft": {
      "invoice_code": "DL",
      "client_name": "Property Owner LLC",
      "property_name": "Downtown Loft Apartments",
      "client_address": "123 Main Street",
      "client_zip_code": "10001",
      "client_city": "New York, NY",
      "client_id": "TAX-12345"
    }
  },
  "source_cells": {
    "renta_mensual": "E37",
    "ganancia_mensual": "E38",
    "percentage": "H38",
    "comision_devomart": "H39"
  },
  "invoice_mapping": {
    "invoice_number": "B16",
    "invoice_date": "B14",
    "client_name": "E7",
    "property_name": "B22",
    "table_start_row": 26,
    "table_start_col": "A",
    "commission_total_cell": "H36"
  }
}
```

### 2. Create Invoice Template

1. Create Google Sheet for invoice template
2. Design layout:
   - Header (invoice #, date, client info)
   - Table (months, rent, profit, fee%, fee amount)
   - Total commission cell
3. Note cell references for `invoice_mapping`
4. Share with service account (Editor access)
5. Copy spreadsheet ID to `template_sheet_id`

### 3. Configure Source Cells

In each month tab of your reservation sheets, ensure cells contain:

- **renta_mensual** (E37): Monthly rent revenue
- **ganancia_mensual** (E38): Monthly profit
- **percentage** (H38): Commission percentage (e.g., 15)
- **comision_devomart** (H39): Commission amount

These are extracted and used in invoice calculation.

## Creating Invoices

### Basic Usage

```bash
# Single month
rez invoice create -a downtown-loft -m january

# Multiple months
rez invoice create -a downtown-loft -m january,february,march

# Quarter
rez invoice create -a downtown-loft -m q1

# Full year
rez invoice create -a downtown-loft -m all
```

### Options

- `-a, --apartment` - Apartment name (required)
- `-m, --months` - Comma-separated months or shortcut
- `-y, --year` - Year for config (default: 2026)
- `--test` - Use test config and TEST_ numbering
- `-e, --email` - Additional emails to share invoice with

### Month Shortcuts

| Shortcut | Expands To |
|----------|------------|
| `q1` | january,february,march |
| `q2` | april,may,june |
| `q3` | july,august,september |
| `q4` | october,november,december |
| `all` | Full year (january-december) |

### Examples

```bash
# Q1 invoice
rez invoice create -a downtown-loft -m q1

# Custom range
rez invoice create -a downtown-loft -m january,march,may

# Test invoice
rez invoice create -a downtown-loft -m january --test

# Share with additional email
rez invoice create -a downtown-loft -m q1 -e client@example.com
```

## Invoice Numbering

Invoices are automatically numbered:

### Production Invoices

```
DL_0001  # Downtown Loft invoice #1
DL_0002  # Downtown Loft invoice #2
BV_0001  # Beachside Villa invoice #1
```

Format: `{CODE}_{NUMBER}`
- CODE: From `invoice_code` in config
- NUMBER: Sequential, 4 digits, zero-padded

### Test Invoices

Separate numbering with TEST_ prefix:

```bash
rez invoice create -a downtown-loft -m january --test
# Creates: TEST_DL_0001
```

Test invoices:
- Use `{apartment}_{year}_test.json` config
- Don't affect production numbering
- Separate tracking

## Invoice Output

### Console Output

```
======================================================================
  📄 INVOICE CREATION (PRODUCTION)
======================================================================
📂 Loading configurations...
🔐 Authenticating...
🔢 Invoice number: DL_0003
📅 Invoice date: 15/02/2026
📅 Extracting data for 3 month(s)...
   → January...
   → February...
   → March...
✅ Data aggregated
   Commission Total: 2475.50
📝 Opening invoice template...
🧹 Cleaning template (preserving formatting)...
✅ Template cleaned
✏️  Populating invoice...
📄 Generating PDF export link...
✅ PDF export link ready

======================================================================
  ✅ INVOICE CREATED
======================================================================
Invoice Number: DL_0003
Invoice Date: 15/02/2026

📄 PDF Export Link:
   https://docs.google.com/spreadsheets/d/.../export?format=pdf&size=A4

🔗 View/Edit Spreadsheet:
   https://docs.google.com/spreadsheets/d/.../edit

📤 Accessible by: your.email@example.com, client@example.com

ℹ️  Click the PDF link above to download invoice as PDF
```

### Invoice Metadata

Metadata saved to `invoices/{apartment}/{invoice_number}.json`:

```json
{
  "invoice_number": "DL_0003",
  "invoice_date": "15/02/2026",
  "apartment": "downtown-loft",
  "months": ["january", "february", "march"],
  "year": 2026,
  "test_mode": false,
  "created_at": "2026-02-15T10:30:00",
  "spreadsheet_id": "1ABC...XYZ",
  "shared_with": ["your.email@example.com", "client@example.com"],
  "commission_total": 2475.50,
  "owner_info": {
    "invoice_code": "DL",
    "property_name": "Downtown Loft",
    "client_name": "Property Owner LLC",
    "client_address": "123 Main Street",
    "client_zip_code": "10001",
    "client_city": "New York, NY",
    "client_id": "TAX-12345"
  }
}
```

> **⚠️ Important: Invoice Links Are Temporary**
> 
> The PDF export link and Google Sheet link displayed after invoice creation are **temporary**:
> - The PDF link is generated on-the-fly each time and **will be overwritten** when the next invoice is created
> - The spreadsheet link is a one-time copy of the template - new invoices don't overwrite previous ones, but the links stored in metadata become stale
> - **Download the PDF immediately** after creating an invoice if you need to keep it
> 
> This is a limitation of the Google Sheets API - the service account cannot create new files in your Google Drive. Each invoice is created as a copy of the template, but the PDF must be exported at the moment of creation.
> 
> **Future improvement ideas:**
> - Save PDF to local filesystem automatically
> - Upload PDFs to a dedicated Google Drive folder
> - Create permanent Google Drive links

## Invoice Management

### List Invoices

```bash
rez invoice list -a downtown-loft
```

Shows:
```
📄 INVOICES FOR downtown-loft

Production:
  DL_0001 - 2026-01-15 - Q1 2026 - 2,350.00
  DL_0002 - 2026-04-15 - Q2 2026 - 2,480.50
  DL_0003 - 2026-07-15 - Q3 2026 - 2,475.50

Test:
  TEST_DL_0001 - 2026-01-10 - January 2026 - 750.00
```

## PDF Export

### Direct Download

The PDF export link directly downloads the spreadsheet as PDF:

```
https://docs.google.com/spreadsheets/d/{ID}/export?format=pdf&size=A4
```

- Click to download
- No authentication needed (if sheet is shared)
- A4 size
- Includes all formatting

### Customizing PDF

Edit `scripts/create_invoice.py` function `generate_pdf_export_link()`:

```python
params = {
    'format': 'pdf',
    'size': 'A4',        # A3, A4, A5, Letter, Legal
    'portrait': 'true',   # or 'false' for landscape
    'scale': 'normal',    # 'fit-width', 'fit-height'
    'gridlines': 'false'
}
```

## Advanced Features

### Fee Percentage Handling

The system automatically:
1. Reads percentage from reservation sheet (e.g., "15" or "15%")
2. Converts to decimal (15 → 0.15)
3. Writes to invoice
4. Google Sheets formats as percentage automatically

### Template Cleanup

Before populating, the system:
- Clears all cells that will be updated
- Preserves formatting (borders, colors, fonts)
- Ensures blank slate for new data
- Prevents data overlap from previous invoices

### Multi-Month Tables

Invoice table dynamically handles:
- 1 month: Single row
- 3 months: Three rows (Q1, Q2, Q3, Q4)
- 12 months: Full year

Always reserves 12 rows in template for maximum flexibility.

## Troubleshooting

### Invoice config not found

```bash
rez invoice config  # Edit config
ls config/invoices.json       # Check exists
```

### Template not found

Verify `template_sheet_id` in `config/invoices.json`.

### Source cell error

Check month tabs have cells at configured locations:
- E37, E38, H38, H39 (or your custom cells)

### Permission denied

Ensure service account has Editor access to:
- Template spreadsheet
- All apartment spreadsheets

### Wrong commission total

Verify:
1. Source cells (H38, H39) have correct formulas
2. Percentage properly formatted
3. Fee calculation correct in reservation sheets

## Best Practices

1. **Use quarters** for regular invoices (q1, q2, q3, q4)
2. **Test first** with `--test` flag
3. **Back up template** before major changes
4. **Track invoices** in separate spreadsheet or system
5. **Version template** for year-over-year consistency

## Examples

### Monthly Invoice Workflow

```bash
# End of Q1
rez invoice create -a downtown-loft -m q1 -e owner@property.com

# Download PDF from link
# Send to property owner
# Archive invoice JSON for records
```

### Annual Summary

```bash
# End of year
rez invoice create -a downtown-loft -m all

# Creates invoice with all 12 months
# Total commission for entire year
```

### Testing New Template

```bash
# Create test invoice
rez invoice create -a downtown-loft -m january --test

# Review output
# Adjust template as needed
# Re-run until perfect

# Switch to production
rez invoice create -a downtown-loft -m january
```

## Next Steps

- 📊 Customize invoice template
- 🧹 Automate monthly/quarterly invoicing
- 📅 Set calendar reminders for invoice generation
- 📧 Set up email automation for PDF delivery
