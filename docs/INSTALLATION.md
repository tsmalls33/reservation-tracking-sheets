# Installation Guide

## Prerequisites

- **Python 3.9+** installed
- **pip** package manager
- **Git** for cloning repository
- **Google Cloud account** (free tier works)

## Step-by-Step Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/reservation-tracking-sheets.git
cd reservation-tracking-sheets
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `click>=8.0` - CLI framework
- `gspread>=6.0` - Google Sheets API
- `pandas>=2.0` - Data processing
- `google-auth>=2.0` - Google authentication

### 3. Install CLI Tool

```bash
pip install -e .
```

The `-e` flag installs in "editable" mode:
- Changes to code take effect immediately
- No need to reinstall after modifications
- Makes `rez` command available globally

### 4. Verify Installation

```bash
rez --version
rez --help
```

You should see:

```
Reservation Tracking System - Automate Airbnb/Booking data to Google Sheets.
...
```

## Google Cloud Setup

### 1. Create Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **New Project**
3. Name it "Reservation Tracking" (or your choice)
4. Click **Create**

### 2. Enable Google Sheets API

1. In your project, go to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click **Enable**

### 3. Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Name: "reservation-sheets" (or your choice)
4. Click **Create and Continue**
5. Skip optional steps, click **Done**

### 4. Download Credentials

1. Click on your service account email
2. Go to **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Choose **JSON** format
5. Click **Create** - file downloads automatically

### 5. Install Credentials

```bash
# Create credentials folder
mkdir -p credentials

# Move downloaded file
mv ~/Downloads/your-project-*.json credentials/service_account.json

# Verify
ls -la credentials/service_account.json
```

## First Configuration

### 1. Create Your Google Sheet

1. Create new Google Sheet
2. Set up month tabs: January, February, etc.
3. Note the spreadsheet ID from URL:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```

### 2. Share With Service Account

1. Run `rez share` to display the service account email
2. In your Google Sheet, click **Share**
3. Paste the service account email
4. Grant **Editor** access
5. **Uncheck** "Notify people" (it's a robot, not a person!)
6. Click **Share**

### 3. Create Apartment Configuration

```bash
rez config create -a downtown-loft -y 2026
```

This creates `config/downtown-loft_2026.json` with a template.

### 4. Edit Configuration

Open `config/downtown-loft_2026.json` and update:

```json
{
  "spreadsheet_id": "PASTE_YOUR_SPREADSHEET_ID_HERE",
  "language": "en",
  "tabs": {
    "january_reservations": {
      "tab_name": "January",
      "start_range": "F11",
      ...
    }
  }
}
```

See [Configuration Guide](CONFIGURATION.md) for full details.

## Shell Completion (Optional)

Enable tab-completion for `--apartment`, `--months`, and `--year` options. Add one line to your shell profile:

| Shell | File | Line to add |
|-------|------|-------------|
| Bash | `~/.bashrc` | `eval "$(_REZ_COMPLETE=bash_source rez)"` |
| Zsh | `~/.zshrc` | `eval "$(_REZ_COMPLETE=zsh_source rez)"` |
| Fish | `~/.config/fish/config.fish` | `_REZ_COMPLETE=fish_source rez \| source` |

Then restart your terminal or source the file (e.g., `source ~/.bashrc`).

## Testing Installation

### Quick Test

```bash
# List configurations
rez config list

# Should show: downtown-loft_2026
```

### Test Upload (Dry Run)

Create a test CSV with sample data:

```csv
Actividad,Entrada,Salida,Precio
John Smith (2),2026-01-15,2026-01-18,450.00
```

Upload to test config:

```bash
rez upload test.csv -a downtown-loft --test
```

## Troubleshooting

### Command not found: rez

Reinstall the CLI:

```bash
cd /path/to/reservation-tracking-sheets
pip install -e .
```

### ModuleNotFoundError: No module named 'cli'

Same solution - reinstall:

```bash
pip install -e .
```

### Permission denied (Google Sheets)

1. Run `rez share` to get the service account email
2. Verify it has access to the spreadsheet
3. Check it has "Editor" permission
4. Try re-sharing the sheet

### Credentials not found

Ensure file is at:

```bash
ls credentials/service_account.json
```

If not, download again from Google Cloud Console.

## Updating

To get latest changes:

```bash
cd /path/to/reservation-tracking-sheets
git pull
pip install -e .  # Reinstall if package structure changed
```

## Uninstalling

```bash
pip uninstall reservations
rm -rf /path/to/reservation-tracking-sheets
```

## Next Steps

- ✅ Installed and configured
- 📖 Read [Configuration Guide](CONFIGURATION.md) for advanced setup
- 🧾 Check [Invoice System](INVOICES.md) for invoice generation
- 🚀 Start uploading reservation data!
