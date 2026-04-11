# Configuration Guide

This guide covers apartment configurations, column mappings, and advanced features.

## Configuration Files

### Location

All configurations live in `config/`:

```
config/
├── downtown-loft_2026.json          # Production config
├── downtown-loft_2026_test.json     # Test config
├── beachside-villa_2026.json        # Another apartment
└── invoices.json                     # Invoice settings
```

### Naming Convention

- **Production**: `{apartment}_{year}.json`
- **Test**: `{apartment}_{year}_test.json`

Test configs:
- Use separate spreadsheet for testing
- Keep production data safe
- Experiment without risk

## Creating Configurations

### Using CLI (Recommended)

```bash
rez config create
```

Interactive wizard that:
- Prompts you to select a template config
- Asks for apartment name and year
- Gets Google Sheet ID
- Sets language (auto-translates tab names)

### Manual Creation

Copy existing config and modify:

```bash
cp config/downtown-loft_2026.json config/beachside-villa_2026.json
# Edit beachside-villa_2026.json
```

## Configuration Structure

### Basic Structure

```json
{
  "spreadsheet_id": "1ABC...XYZ",
  "language": "en",
  "tabs": {
    "january_reservations": { ... },
    "february_reservations": { ... }
  }
}
```

### Spreadsheet ID

From Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/[COPY_THIS_PART]/edit
```

### Language

- `"en"` - English month names (January, February, ...)
- `"es"` - Spanish month names (Enero, Febrero, ...)

Affects:
- Tab names in Google Sheets
- Month display in cell B2
- Invoice language

## Tab Configuration

### Tab Structure

```json
"january_reservations": {
  "tab_name": "January",
  "start_range": "F11",
  "physical_columns": 8,
  "columns": [
    "Guest",
    "Paid",
    "Check-in",
    "Check-out",
    "Nights",
    "Price",
    "Cleaning",
    "Commission"
  ],
  "column_mapping": { ... }
}
```

### Fields

- **`tab_name`**: Exact tab name in Google Sheets (whitespace ignored)
- **`start_range`**: Top-left cell to start writing data (e.g., "F11")
- **`physical_columns`**: Number of actual columns in sheet (for clearing)
- **`columns`**: Ordered list of column names
- **`column_mapping`**: How CSV fields map to sheet columns

### Why physical_columns?

If your sheet has merged cells or spans more columns than data:

```
Sheet:  A | B | C | D | E | F | G | H | I
Data:       | Guest    | Date | Nights  |     <- Merged cells
```

Set `physical_columns: 9` to clear all columns A-I.

## Column Mapping

### Simple Mapping

One CSV field → One sheet column:

```json
"column_mapping": {
  "Guest": {
    "csv_field": "Actividad",
    "sheet_col_offset": 0
  },
  "Check-in": {
    "csv_field": "Entrada",
    "sheet_col_offset": 2
  }
}
```

**Fields:**
- `csv_field`: Column name from processed CSV
- `sheet_col_offset`: Position in the row (0-based)

### Calculated Fields

Multiple CSV fields → One sheet column:

```json
"Total Price": {
  "csv_fields": ["Precio", "Comision"],
  "operation": "sum",
  "sheet_col_offset": 6
}
```

Adds `Precio` + `Comision` and writes to offset 6.

**Supported operations:**
- `sum`: Add all fields together

### Offset Explained

If `start_range: "F11"`:

| Offset | Column | Description |
|--------|--------|-------------|
| 0 | F | First column |
| 1 | G | Second column |
| 2 | H | Third column |
| 3 | I | Fourth column |

Example:
```json
"Guest": { "sheet_col_offset": 0 }     // Column F
"Paid": { "sheet_col_offset": 1 }      // Column G
"Check-in": { "sheet_col_offset": 2 }  // Column H
```

## CSV Field Names

Processed CSVs have standardized columns:

| CSV Column | Description | Source |
|------------|-------------|--------|
| `Actividad` | Guest name + count | Both |
| `Pagado` | Payment status | Both |
| `Entrada` | Check-in date | Both |
| `Salida` | Check-out date | Both |
| `Noches` | Number of nights | Both |
| `Precio` | Booking price | Both |
| `Check In/Out` | Cleaning fee | Both |
| `Comision` | Platform commission | Both |

## Advanced Features

### Multiple Configs Per Apartment

Different years:

```
config/
├── downtown-loft_2025.json
├── downtown-loft_2026.json
└── downtown-loft_2027.json
```

Specify year:
```bash
rez upload data.csv -a downtown-loft -y 2025
```

### Test Configurations

Development/testing - create a separate test config that points to a different spreadsheet:

```bash
# Run config create and select "Yes" when asked to create as test config
rez config create

# Use test config
rez upload data.csv -a downtown-loft --test
```

Test configs:
- Point to different spreadsheet
- Safe experimentation
- No production impact

### Shared Configurations

Multiple apartments with same structure:

```bash
# Base config
cp config/downtown-loft_2026.json config/beachside-villa_2026.json

# Update only spreadsheet_id
vim config/beachside-villa_2026.json
```

## Configuration Management

### List Configs

```bash
rez config list
```

Shows:
```
📋 APARTMENT CONFIGURATIONS

downtown-loft:
  • downtown-loft_2026.json
  • downtown-loft_2026_test.json

beachside-villa:
  • beachside-villa_2026.json
```

### Delete Configs

```bash
rez config delete
```

Interactive - shows numbered list and prompts for selection.

## Validation

### Common Errors

**"spreadsheet_id" not found**
```json
{
  "spreadsheet_id": "YOUR_ID_HERE",  // ❌ Forgot to update
  ...
}
```

**Tab name mismatch**
```json
"tab_name": "January"  // ❌ Sheet says "Jan"
```

**Invalid JSON**
```json
{
  "key": "value",  // ❌ Trailing comma
}
```

Validate JSON: https://jsonlint.com/

### Testing Configs

Test upload with minimal data:

```bash
# Create test.csv with one row
rez upload test.csv -a downtown-loft --test
```

Check:
- ✅ Correct sheet opened
- ✅ Data in right tab
- ✅ Columns aligned
- ✅ Formatting preserved

## Best Practices

1. **Use test configs** for experiments
2. **Backup before changes**: `cp config/apt.json config/apt.json.backup`
3. **Validate JSON** before saving
4. **Document custom fields** in comments (if needed)
5. **Version control** your configs (but not `credentials/`!)

## Examples

### Minimal Config

```json
{
  "spreadsheet_id": "1ABC...XYZ",
  "language": "en",
  "tabs": {
    "january_reservations": {
      "tab_name": "January",
      "start_range": "A1",
      "physical_columns": 5,
      "columns": ["Guest", "Check-in", "Check-out", "Nights", "Price"],
      "column_mapping": {
        "Guest": {"csv_field": "Actividad", "sheet_col_offset": 0},
        "Check-in": {"csv_field": "Entrada", "sheet_col_offset": 1},
        "Check-out": {"csv_field": "Salida", "sheet_col_offset": 2},
        "Nights": {"csv_field": "Noches", "sheet_col_offset": 3},
        "Price": {"csv_field": "Precio", "sheet_col_offset": 4}
      }
    }
  }
}
```

### With Calculated Field

```json
"Total": {
  "csv_fields": ["Precio", "Check In/Out", "Comision"],
  "operation": "sum",
  "sheet_col_offset": 8
}
```

## Troubleshooting

### Config not found

```bash
rez config list  # Check available configs
ls config/                # Check file names
```

### Data in wrong columns

Verify `sheet_col_offset` values:
```bash
rez upload test.csv -a downtown-loft --test
```

Check alignment, adjust offsets.

### Formatting cleared

Increase `physical_columns` to match actual sheet columns.

## Next Steps

- 📊 See [Data Management](DATA_MANAGEMENT.md) for file handling
- 🧾 See [Invoice System](INVOICES.md) for invoice setup
- 🏗️ See [CLI Architecture](CLI_ARCHITECTURE.md) for technical details
