# 📊 Reservation Tracking Sheets

> **Automate Airbnb and Booking.com reservations to Google Sheets with intelligent processing and invoice generation**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

- 🤖 **Auto-Detection**: Automatically detects Airbnb or Booking.com CSV formats
- 📅 **Smart Processing**: Filters cancelled bookings, normalizes dates, standardizes formats
- 📤 **Intelligent Upload**: Only updates affected months, preserves sheet formatting
- 🧾 **Invoice Generation**: Create professional invoices from reservation data
- 🧹 **Auto-Cleanup**: Temporary files automatically deleted after processing
- 🌍 **Multi-Language**: Supports English and Spanish month names
- ⚡ **One Command**: Process multiple files and upload in a single command

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/reservation-tracking-sheets.git
cd reservation-tracking-sheets

# Install dependencies
pip install -r requirements.txt

# Install CLI in development mode
pip install -e .
```

### Setup

1. **Google Cloud Setup**
   - Create a [Google Cloud Project](https://console.cloud.google.com/)
   - Enable Google Sheets API
   - Create a service account and download JSON key
   - Save as `credentials/service_account.json`

2. **Share Your Sheet**
   - Run `reservations share` to display the service account email
   - Open your Google Sheet and click **Share**
   - Paste the email and grant "Editor" access

3. **Configure Apartment**
   ```bash
   reservations config create
   ```
   Follow the interactive prompts to create your apartment configuration.

### Basic Usage

```bash
# Upload single CSV
reservations upload airbnb_export.csv -a downtown-loft

# Upload multiple files (auto-merges)
reservations upload airbnb.csv booking.csv -a downtown-loft

# Create invoice for specific months
reservations invoice create -a downtown-loft -m january,february

# Get service account email for Google Sheets sharing
reservations share

# View apartment's Google Sheet
reservations open -a downtown-loft
```

## Global Options

- `-v, --verbose` - Enable verbose output for debugging

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[CLI Architecture](docs/CLI_ARCHITECTURE.md)** - Technical overview of the CLI structure
- **[Configuration Guide](docs/CONFIGURATION.md)** - Setting up apartment configs and mappings
- **[Data Management](docs/DATA_MANAGEMENT.md)** - How temporary files are handled
- **[Invoice System](docs/INVOICES.md)** - Creating and managing invoices

## 🎯 Commands

### Upload Reservations

```bash
reservations upload [FILES...] -a APARTMENT [-y YEAR] [-H] [--test] [--keep-source]
```

**Options:**
- `-a, --apartment` - Apartment name (required)
- `-y, --year` - Year for config (default: 2026)
- `-H, --hard-replace` - Clear all month tabs before upload
- `--test` - Use test configuration
- `--keep-source` - Keep original CSV files after upload (default: deletes them)

**Examples:**
```bash
# Single file
reservations upload bookings.csv -a downtown-loft

# Multiple files (auto-merges Airbnb + Booking.com)
reservations upload airbnb.csv booking.csv -a downtown-loft

# Test mode
reservations upload data.csv -a downtown-loft --test

# Clear all months first
reservations upload data.csv -a downtown-loft -H

# Keep original CSV files
reservations upload data.csv -a downtown-loft --keep-source
```

### Invoice Management

```bash
# Create invoice
reservations invoice create -a APARTMENT -m MONTHS [-y YEAR] [--test] [-e EMAIL]

# List invoices
reservations invoice list -a APARTMENT

# Configure invoice settings
reservations invoice config
```

**Examples:**
```bash
# Single month
reservations invoice create -a downtown-loft -m january

# Multiple months
reservations invoice create -a downtown-loft -m january,february,march

# Quarter
reservations invoice create -a downtown-loft -m q1

# Entire year
reservations invoice create -a downtown-loft -m all
```

### Configuration

```bash
# List configurations
reservations config list

# Create new configuration (interactive)
reservations config create

# Delete configuration (interactive)
reservations config delete
```

### Share

```bash
# Display service account email for Google Sheets sharing
reservations share
```

### Quick Access

```bash
# Open project in Neovim
reservations open

# View apartment's Google Sheet (displays clickable link)
reservations open -a downtown-loft

# View test sheet for specific year
reservations open -a downtown-loft -y 2025 --test
```

## ⌨️ Shell Completion (Optional)

Enable tab-completion for apartment names, months, and years. Add **one line** to your shell profile:

**Bash** (`~/.bashrc`):
```bash
eval "$(_RESERVATIONS_COMPLETE=bash_source reservations)"
```

**Zsh** (`~/.zshrc`):
```bash
eval "$(_RESERVATIONS_COMPLETE=zsh_source reservations)"
```

**Fish** (`~/.config/fish/config.fish`):
```fish
_RESERVATIONS_COMPLETE=fish_source reservations | source
```

Then restart your shell or `source` the file. After that:
```
reservations upload data.csv -a <TAB>       → duplex  mediona  sant-domenec ...
reservations invoice create -m <TAB>        → jan  feb  ... q1  q2  ... all
reservations open -y <TAB>                  → 2025  2026
```

## 🏗️ Project Structure

```
reservation-tracking-sheets/
├── cli/                       # Modular CLI commands
│   ├── commands/              # Individual command modules
│   │   ├── upload.py          # Upload command
│   │   ├── invoice.py         # Invoice management
│   │   ├── config.py          # Config management
│   │   ├── open_project.py    # Project/sheet access
│   │   └── share.py           # Service account email display
│   └── utils/                 # Shared utilities
├── scripts/                   # Data processing scripts
│   ├── process_airbnb.py      # Airbnb CSV processor
│   ├── process_booking.py     # Booking.com processor
│   ├── merge_data.py          # Multi-file merger
│   ├── upload_to_sheets.py    # Google Sheets uploader
│   └── create_invoice.py      # Invoice generator
├── config/                    # Apartment configurations
│   ├── downtown-loft_2026.json
│   └── invoices.json
├── credentials/               # Google service account
│   └── service_account.json
├── docs/                      # Documentation
└── data/temp/                 # Auto-deleted temp files
```

## 🔧 Configuration

Each apartment has a JSON configuration defining:
- Google Sheet ID
- Tab names (localized)
- Cell ranges
- Column mappings
- Calculated fields

**Example:** `config/downtown-loft_2026.json`

```json
{
  "spreadsheet_id": "1ABC...XYZ",
  "language": "en",
  "tabs": {
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
      "column_mapping": {
        "Guest": {
          "csv_field": "Actividad",
          "sheet_col_offset": 0
        },
        "Price": {
          "csv_fields": ["Precio", "Comision"],
          "operation": "sum",
          "sheet_col_offset": 5
        }
      }
    }
  }
}
```

See [Configuration Guide](docs/CONFIGURATION.md) for details.

## 🎨 Output Format

Processed data includes:

| Column | Description | Format |
|--------|-------------|--------|
| Guest | Guest name + count | "John Smith (2)" |
| Paid | Payment status | "Paid" / "Pending" |
| Check-in | Arrival date | YYYY-MM-DD |
| Check-out | Departure date | YYYY-MM-DD |
| Nights | Stay duration | Integer |
| Price | Booking price | Decimal (no symbol) |
| Cleaning | Cleaning fee | Decimal (no symbol) |
| Commission | Platform fee | Decimal (no symbol) |

## 🧾 Invoice Features

- **Auto-numbering**: Sequential invoice numbers per apartment
- **Multi-month**: Combine multiple months in one invoice
- **PDF Export**: Direct PDF download link
- **Test Mode**: Separate TEST_ invoice numbering
- **Metadata**: Local JSON tracking of all invoices

## 🔐 Security

- ✅ Service account credentials stored locally only
- ✅ Temporary files auto-deleted
- ✅ No data stored in repository
- ✅ `.gitignore` includes `credentials/`, `data/`, `invoices/`

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'cli'

```bash
cd ~/path/to/reservation-tracking-sheets
pip install -e .
```

### Config not found

Check naming: `{apartment}_{year}.json` or `{apartment}_{year}_test.json`

```bash
reservations config list  # See available configs
```

### Worksheet not found

Verify tab names in config match Google Sheet (whitespace ignored).

### Permission denied (Google Sheets)

Run `reservations share` to get the service account email, then ensure it has "Editor" access to the spreadsheet.

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI
- [gspread](https://gspread.readthedocs.io/) for Google Sheets API
- [pandas](https://pandas.pydata.org/) for data processing

## 📧 Support

For issues and questions:
- 📫 Open an issue on GitHub
- 📖 Check the [documentation](docs/)
- 💡 Review existing issues for solutions

---

**Made with ❤️ for vacation rental managers**
