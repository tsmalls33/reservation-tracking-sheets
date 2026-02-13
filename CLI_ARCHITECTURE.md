# CLI Architecture Documentation

This document explains the modular structure of the Reservations CLI application.

## Overview

The CLI has been refactored from a single monolithic `main.py` file (~1,200 lines) into a clean, modular structure following Click best practices.

## Directory Structure

```
reservation-tracking-sheets/
├── main.py                      # Entry point (~20 lines)
├── cli/
│   ├── __init__.py             # Main CLI group + context setup
│   ├── constants.py            # Month names, abbreviations, groups
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── upload.py           # Upload command
│   │   ├── open_project.py     # Open/source commands
│   │   ├── config.py           # Config group (list/create/delete)
│   │   └── invoice.py          # Invoice group (config/create/list)
│   └── utils/
│       ├── __init__.py
│       ├── config.py           # Config file utilities
│       ├── platform.py         # Platform detection
│       ├── months.py           # Month parsing/translation
│       └── display.py          # Consistent output formatting
├── scripts/                    # Data processing scripts
└── config/                     # Configuration files
```

## Key Components

### Entry Point: `main.py`

Minimal entry point that imports and runs the CLI:

```python
from cli import cli

if __name__ == '__main__':
    cli()
```

### CLI Package: `cli/__init__.py`

- Defines the main CLI group with version and help text
- Sets up Click context with `PROJECT_ROOT` and `CONFIG_DIR`
- Registers all command groups and commands
- Exports `PROJECT_ROOT` and `CONFIG_DIR` for use in all modules

### Constants: `cli/constants.py`

Centralized constants:
- `MONTH_NAMES`: English/Spanish translations
- `MONTH_ABBREV`: Abbreviations to full names
- `MONTH_GROUPS`: Quarter and "all" groupings

### Commands: `cli/commands/`

Each command module is self-contained:

#### `upload.py`
- Single `@click.command()` for CSV upload
- Handles platform detection, processing, merging, and upload

#### `open_project.py`
- `open` command: Opens project in Neovim
- `source` command: Alias for `open`

#### `config.py`
- `@click.group()` with three subcommands:
  - `list`: Show all configurations
  - `create`: Create new config from template
  - `delete`: Delete one or more configs

#### `invoice.py`
- `@click.group()` with three subcommands:
  - `config`: Configure invoice settings
  - `create`: Generate invoice from data
  - `list`: Show all invoices

### Utilities: `cli/utils/`

Reusable helper functions:

#### `config.py`
```python
list_config_files(config_dir: Path) -> dict
```
Returns configs organized by apartment name.

#### `platform.py`
```python
detect_platform(filename: str) -> str
```
Detects if CSV is from Airbnb or Booking.com.

#### `months.py`
```python
parse_months(month_input: str) -> list
translate_tab_names(config_data: dict, target_language: str) -> dict
```
Handles month parsing and tab name translation.

#### `display.py`
```python
success(message: str) -> None
error(message: str) -> None
info(message: str) -> None
warning(message: str) -> None
section_header(title: str) -> None
```
Consistent CLI output formatting with colors and emojis.

## Import Pattern

All modules follow this import pattern:

```python
# From main CLI package
from .. import PROJECT_ROOT, CONFIG_DIR

# From constants
from ..constants import MONTH_NAMES, MONTH_ABBREV, MONTH_GROUPS

# From utilities
from ..utils.config import list_config_files
from ..utils.platform import detect_platform
from ..utils.months import parse_months, translate_tab_names
from ..utils.display import success, error, warning
```

## Context Management

The main CLI group uses Click's context to share data:

```python
@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj['project_root'] = PROJECT_ROOT
    ctx.obj['config_dir'] = CONFIG_DIR
```

Commands can access context with:

```python
@click.command()
@click.pass_context
def my_command(ctx):
    project_root = ctx.obj['project_root']
```

## Benefits of This Structure

### 1. **Modularity**
- Each command in its own file
- Easy to locate and modify specific functionality
- Clear separation of concerns

### 2. **Reusability**
- Utilities can be imported anywhere
- Consistent display functions throughout
- Shared constants avoid duplication

### 3. **Maintainability**
- Small, focused files (< 300 lines each)
- Clear dependencies
- Easy to test individual components

### 4. **Scalability**
- Add new commands without modifying existing code
- Extend utilities without affecting commands
- Register new command groups in one place

### 5. **Type Safety**
- Type hints on all utility functions
- Clear function signatures
- Better IDE support

## Adding New Commands

### 1. Create command module

```python
# cli/commands/my_command.py
import click
from .. import PROJECT_ROOT
from ..utils.display import success, error

@click.command()
@click.option('--option', '-o', help='Some option')
def my_command(option):
    """Description of my command."""
    success("Command executed!")
```

### 2. Register in `cli/__init__.py`

```python
def register_commands():
    from .commands import config, invoice, upload, open_project, my_command
    
    cli.add_command(config.config)
    cli.add_command(invoice.invoice)
    cli.add_command(upload.upload)
    cli.add_command(open_project.open_cmd)
    cli.add_command(open_project.source)
    cli.add_command(my_command.my_command)  # Add this
```

### 3. Update `cli/commands/__init__.py`

```python
from . import config, invoice, upload, open_project, my_command

__all__ = ['config', 'invoice', 'upload', 'open_project', 'my_command']
```

## Testing Strategy

### Unit Tests
- Test utility functions independently
- Mock Click context for commands
- Verify output formatting

### Integration Tests
- Test command execution
- Verify file operations
- Check subprocess calls

### Example Test Structure
```
tests/
├── test_utils/
│   ├── test_config.py
│   ├── test_platform.py
│   ├── test_months.py
│   └── test_display.py
└── test_commands/
    ├── test_upload.py
    ├── test_config.py
    └── test_invoice.py
```

## Performance

- Lazy imports in commands (only loaded when used)
- No performance impact from modularization
- Same execution speed as monolithic version

## Migration Notes

The refactoring maintains 100% backward compatibility:
- All CLI commands work identically
- Same arguments and options
- Same output format
- No changes to external scripts or config files

## Future Enhancements

1. **Add type hints**: Complete typing for all functions
2. **Add docstrings**: Document all modules comprehensively
3. **Create tests**: Unit and integration test suite
4. **Add logging**: Structured logging with levels
5. **Configuration class**: Replace dict-based config
6. **Custom exceptions**: Better error handling hierarchy
