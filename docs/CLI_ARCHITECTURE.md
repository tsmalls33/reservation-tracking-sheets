# CLI Architecture

Modular CLI structure using Click framework for the Reservation Tracking System.

## Overview

The CLI is organized into:
- **Main entry point**: `cli/__init__.py`
- **Command modules**: `cli/commands/*.py`
- **Utilities**: `cli/utils/*.py`
- **Processing scripts**: `scripts/*.py`

## Structure

```
reservation-tracking-sheets/
├── cli/
│   ├── __init__.py              # Main CLI group
│   ├── commands/
│   │   ├── __init__.py          # Command exports
│   │   ├── upload.py            # Upload command
│   │   ├── invoice.py           # Invoice commands
│   │   ├── config.py            # Config management
│   │   ├── open_project.py      # Open/view commands
│   │   └── docs.py              # Documentation command
│   └── utils/
│       ├── display.py           # Output formatting
│       ├── platform.py          # Platform detection
│       └── validation.py        # Input validation
├── scripts/
│   ├── process_airbnb.py        # Airbnb processor
│   ├── process_booking.py       # Booking processor
│   ├── merge_data.py            # File merger
│   ├── upload_to_sheets.py      # Sheets uploader
│   └── create_invoice.py        # Invoice generator
└── main.py                      # Entry point
```

## Command Registration

### Main CLI Group

`cli/__init__.py`:

```python
import click
from .commands import upload, invoice, config, open_project, docs

@click.group()
@click.version_option(version='2.0.0')
def cli():
    """Reservation Tracking System."""
    pass

# Register commands
cli.add_command(upload.upload)
cli.add_command(invoice.invoice)
cli.add_command(config.config)
cli.add_command(open_project.open_cmd)
cli.add_command(docs.docs)
```

### Command Modules

Each command in `cli/commands/*.py`:

```python
import click

@click.command()
@click.argument('file')
@click.option('--apartment', '-a', required=True)
def upload(file, apartment):
    """Upload reservations to Google Sheets."""
    # Implementation
    pass
```

## Command Groups

### Invoice Group

`cli/commands/invoice.py` implements subcommands:

```python
@click.group()
def invoice():
    """Invoice management."""
    pass

@invoice.command('create')
def create():
    """Create invoice."""
    pass

@invoice.command('list')
def list_invoices():
    """List invoices."""
    pass
```

Usage:
```bash
reservations invoice create -a apt -m jan
reservations invoice list -a apt
```

### Config Group

```python
@click.group()
def config():
    """Configuration management."""
    pass

@config.command('list')
@config.command('create')
@config.command('delete')
```

Usage:
```bash
reservations config list
reservations config create -a apt
reservations config delete apt_2025
```

## Utilities

### Display Utilities

`cli/utils/display.py`:

```python
import click

def success(message):
    click.echo(click.style(f"✅ {message}", fg='green'))

def error(message):
    click.echo(click.style(f"❌ {message}", fg='red'), err=True)

def info(message):
    click.echo(click.style(f"ℹ️  {message}", fg='blue'))

def section_header(title):
    click.echo(f"\n{'-' * 70}")
    click.echo(f"  {title}")
    click.echo(f"{'-' * 70}")
```

Usage in commands:
```python
from ..utils.display import success, error, section_header

section_header("UPLOADING")
success("Upload complete")
error("Upload failed")
```

### Platform Detection

`cli/utils/platform.py`:

```python
def detect_platform(filepath):
    """Detect Airbnb or Booking.com from filename/content."""
    filename = str(filepath).lower()
    
    # Check filename
    if any(x in filename for x in ['airbnb', 'confirmación', 'hm']):
        return 'airbnb'
    if any(x in filename for x in ['booking', 'reservation']):
        return 'booking'
    
    # Check content
    with open(filepath, 'r') as f:
        content = f.read(1024).lower()
        if 'airbnb' in content:
            return 'airbnb'
        if 'booking' in content:
            return 'booking'
    
    raise ValueError(f"Cannot detect platform for {filepath}")
```

### Validation

`cli/utils/validation.py`:

```python
def validate_apartment(ctx, param, value):
    """Validate apartment name format."""
    if not value:
        return value
    
    if not value.replace('-', '').replace('_', '').isalnum():
        raise click.BadParameter(
            "Apartment name must contain only letters, numbers, hyphens, underscores"
        )
    
    return value

@click.option('--apartment', callback=validate_apartment)
def command(apartment):
    pass
```

## Script Execution

Commands call processing scripts via subprocess:

```python
import subprocess
import sys
from pathlib import Path
from .. import PROJECT_ROOT

script = PROJECT_ROOT / "scripts/process_airbnb.py"
result = subprocess.run([
    sys.executable,
    str(script),
    input_file,
    output_file
], check=True, capture_output=True, text=True)
```

Benefits:
- Scripts can run independently
- Separate concerns (CLI vs processing)
- Easy to test scripts directly
- No import conflicts

## Error Handling

### CLI-Level Errors

```python
try:
    # Command logic
except FileNotFoundError as e:
    error(f"File not found: {e}")
    sys.exit(1)
except Exception as e:
    error(f"Unexpected error: {e}")
    sys.exit(1)
```

### Script-Level Errors

Scripts print to stderr and exit with non-zero:

```python
try:
    # Processing logic
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

CLI catches via `subprocess.CalledProcessError`.

## Configuration Access

Commands access project paths via `cli/__init__.py`:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CONFIG_DIR = PROJECT_ROOT / "config"
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
DATA_DIR = PROJECT_ROOT / "data"
```

Commands import:
```python
from .. import PROJECT_ROOT, CONFIG_DIR
```

## Help Text

### Command Help

```python
@click.command()
def upload():
    """Upload reservation data to Google Sheets.
    
    Automatically detects platform, processes CSVs,
    and uploads to configured spreadsheet.
    
    \\b
    Examples:
      reservations upload data.csv -a apt
      reservations upload a.csv b.csv -a apt
    """
    pass
```

The `\\b` preserves formatting in examples.

### Option Help

```python
@click.option(
    '--apartment', '-a',
    required=True,
    help='Apartment name (matches config file)'
)
@click.option(
    '--test',
    is_flag=True,
    help='Use test configuration ({apartment}_{year}_test.json)'
)
```

## Help Text Location

**Help texts live in two places:**

1. **Docstrings** in command functions (`cli/commands/*.py`):
   - Displayed when running `reservations <command> --help`
   - Written directly in the function docstring
   - Use `\\b` to preserve formatting

2. **Option help** in `@click.option()` decorators:
   - Brief descriptions for each option
   - Displayed in command help output

**Example:**
```python
# cli/commands/upload.py
@click.command()
@click.argument('csv_files', nargs=-1)
@click.option('--apartment', '-a', required=True, 
              help='Apartment name (matches config file)')
def upload(csv_files, apartment):
    """Upload reservation CSVs to Google Sheets.
    
    Automatically detects platform, processes CSVs,
    and uploads to configured spreadsheet.
    
    \\b
    Examples:
      reservations upload data.csv -a downtown-loft
    """
    # Implementation
```

## Testing

### Manual Testing

```bash
# Install in editable mode
pip install -e .

# Test commands
reservations --help
reservations upload --help
reservations config list
reservations docs
```

### Testing Scripts Directly

```bash
# Test processing script
python scripts/process_airbnb.py input.csv output.csv

# Test uploader
python scripts/upload_to_sheets.py --csv data.csv -a apt -y 2026
```

## Adding New Commands

1. **Create command file**: `cli/commands/new_cmd.py`

```python
import click

@click.command()
@click.argument('arg')
@click.option('--option', '-o')
def new_cmd(arg, option):
    """New command description.
    
    Detailed explanation of what the command does.
    
    \\b
    Examples:
      reservations new-cmd myarg -o value
    """
    click.echo(f"Running new command: {arg}, {option}")
```

2. **Register in `cli/__init__.py`**:

```python
from .commands import new_cmd

cli.add_command(new_cmd.new_cmd)
```

3. **Test**:

```bash
reservations new-cmd myarg --option value
reservations new-cmd --help
```

## Best Practices

1. **One command per file**: Keep files focused
2. **Use command groups**: For related commands (invoice, config)
3. **Shared utilities**: Place in `cli/utils/`
4. **Subprocess for scripts**: Keep processing separate
5. **Rich help text**: Include examples and descriptions
6. **Validation**: Validate inputs early
7. **Error handling**: User-friendly error messages
8. **Progress output**: Show what's happening
9. **Docstrings**: Write comprehensive help text
10. **Test help**: Verify `--help` output is clear

## References

- [Click Documentation](https://click.palletsprojects.com/)
- [Command Line Interface Guidelines](https://clig.dev/)
- [Python subprocess module](https://docs.python.org/3/library/subprocess.html)
