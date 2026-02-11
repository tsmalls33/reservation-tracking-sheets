# Dynamic Column Mapping Documentation

This document explains how the dynamic column mapping system works and how to configure different sheet layouts.

## Overview

The upload system now supports flexible column layouts defined in JSON config files. Each apartment/sheet can have different columns while using the same CSV processing pipeline.

## How It Works

### 1. CSV Processing
Both `process_airbnb.py` and `process_booking.py` output standardized CSV files with these columns:
```
Actividad, Entrada, Salida, Noches, Precio, Check In/Out, Comision, VAT
```

### 2. Config Mapping
Each config file maps CSV columns to sheet columns using `column_mapping`:

#### Simple Field Mapping
```json
"column_mapping": {
  "Sheet Column Name": {
    "csv_field": "CSV_Column_Name",
    "sheet_col_offset": 0,
    "skip_next": true  // optional, for merged cells
  }
}
```

#### Calculated Field Mapping (NEW!)
```json
"column_mapping": {
  "Precio Total": {
    "csv_fields": ["Precio", "Comision"],  // multiple CSV fields
    "operation": "sum",                     // sum them together
    "sheet_col_offset": 4
  }
}
```

### 3. Upload Flexibility
The upload script reads `column_mapping` and `physical_columns` to:
- Clear the correct number of columns
- Place CSV data at the right sheet positions
- Handle merged cells automatically
- **Calculate derived values from multiple CSV fields**

## Configuration Examples

### Mediona Layout (8 physical columns)

**Visible Columns:** Actividad | (merged) | Entrada | Salida | Noches | Precio | Check In/Out | Comision

**Physical Sheet Layout:**
```
F: Actividad (merged with G)
G: (empty, part of F merge)
H: Entrada
I: Salida
J: Noches
K: Precio
L: Check In/Out
M: Comision
```

**Config:**
```json
{
  "columns": ["Actividad", "Entrada", "Salida", "Noches", "Precio", "Check In/Out", "Comision"],
  "column_mapping": {
    "Actividad": {"csv_field": "Actividad", "sheet_col_offset": 0, "skip_next": true},
    "Entrada": {"csv_field": "Entrada", "sheet_col_offset": 2},
    "Salida": {"csv_field": "Salida", "sheet_col_offset": 3},
    "Noches": {"csv_field": "Noches", "sheet_col_offset": 4},
    "Precio": {"csv_field": "Precio", "sheet_col_offset": 5},
    "Check In/Out": {"csv_field": "Check In/Out", "sheet_col_offset": 6},
    "Comision": {"csv_field": "Comision", "sheet_col_offset": 7}
  },
  "physical_columns": 8
}
```

### Sant Domènec Layout (5 physical columns) - WITH CALCULATED FIELD

**Visible Columns:** Nombre Reserva | (merged) | Entrada | Salida | Precio Total

**Physical Sheet Layout:**
```
F: Nombre Reserva (merged with G)
G: (empty, part of F merge)
H: Entrada
I: Salida
J: Precio Total (calculated: Precio + Comision)
```

**Config:**
```json
{
  "columns": ["Nombre Reserva", "Entrada", "Salida", "Precio Total"],
  "column_mapping": {
    "Nombre Reserva": {"csv_field": "Actividad", "sheet_col_offset": 0, "skip_next": true},
    "Entrada": {"csv_field": "Entrada", "sheet_col_offset": 2},
    "Salida": {"csv_field": "Salida", "sheet_col_offset": 3},
    "Precio Total": {"csv_fields": ["Precio", "Comision"], "operation": "sum", "sheet_col_offset": 4}
  },
  "physical_columns": 5
}
```

## Key Concepts

### `sheet_col_offset`
The column position relative to `start_range`. If `start_range` is "F11":
- offset 0 = column F
- offset 1 = column G
- offset 2 = column H
- etc.

### `skip_next: true`
Used when a column is merged with the next one. This accounts for the physical space occupied by merged cells.

### `physical_columns`
Total number of physical columns to clear, including merged cells. This ensures proper clearing without affecting adjacent data.

### `csv_fields` + `operation` (Calculated Fields)
**NEW FEATURE:** You can now compute values from multiple CSV columns.

**Supported Operations:**
- `"sum"`: Add multiple fields together

**Example Use Cases:**
- `Precio Total = Precio + Comision`
- `Total Guests = Adults + Children + Infants`
- `Net Income = Revenue - Commission - Fees`

## CSV to Sheet Mapping

| CSV Field | Mediona Sheet | Sant Domènec Sheet |
|-----------|---------------|--------------------|
| Actividad | Actividad | Nombre Reserva |
| Entrada | Entrada | Entrada |
| Salida | Salida | Salida |
| Noches | Noches | *(not displayed)* |
| Precio | Precio | *(used in calc)* |
| Check In/Out | Check In/Out | *(not displayed)* |
| Comision | Comision | *(used in calc)* |
| **Calculated** | - | **Precio Total** (Precio+Comision) |

## Usage Examples

### Upload to Mediona (detailed breakdown)
```bash
python main.py oneshot file1.csv file2.csv -a mediona -y 2026
```
Shows: Precio and Comision as separate columns

### Upload to Sant Domènec (simplified with total)
```bash
python main.py oneshot file1.csv file2.csv -a sant-domenec -y 2026
```
Shows: Precio Total (automatically calculated as Precio + Comision)

Both use the same CSV processing but map to different sheet layouts automatically!

## Adding New Configurations

1. Identify your sheet layout (starting cell, columns, merged cells)
2. Create config file: `config/{apartment}_{year}.json`
3. Define `column_mapping` with correct offsets
4. Use `csv_field` for direct mapping OR `csv_fields` + `operation` for calculations
5. Set `physical_columns` (count includes merged cells)
6. Run: `python main.py oneshot ... -a {apartment} -y {year}`

## Advanced: Calculated Field Examples

### Sum Multiple Fields
```json
"Total Cost": {
  "csv_fields": ["Precio", "Check In/Out", "Comision"],
  "operation": "sum",
  "sheet_col_offset": 5
}
```

### Future Operations (not yet implemented)
```json
// Could add:
"operation": "average"    // Average of fields
"operation": "max"        // Maximum value
"operation": "subtract"   // Subtract fields
```

## Notes

- All configs start at F11 by default
- F and G are always merged in current layouts
- Clearing affects only data cells, preserves formatting
- Month name is always written to cell B2
- Calculated fields are computed during upload, not in CSV
- Missing CSV fields default to 0 in calculations
