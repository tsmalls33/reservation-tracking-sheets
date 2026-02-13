"""Commands for opening the project in Neovim."""

import os
import sys
import click
from .. import PROJECT_ROOT
from ..utils.display import error


@click.command('open')
def open_cmd():
    """Open the project root directory in Neovim.
    
    Launches Neovim with the project root directory
    (~/dev/reservation-tracking-sheets) as the working directory.
    
    \b
    Example:
      reservations open
    """
    click.echo(f"📂 Opening project in Neovim: {click.style(str(PROJECT_ROOT), fg='cyan')}")
    try:
        # Use os.execvp to replace the current process with nvim
        # This allows nvim to take over the terminal properly
        os.chdir(PROJECT_ROOT)
        os.execvp('nvim', ['nvim', str(PROJECT_ROOT)])
    except FileNotFoundError:
        error("nvim not found. Make sure Neovim is installed.")
        sys.exit(1)
    except Exception as e:
        error(f"Error opening Neovim: {e}")
        sys.exit(1)


@click.command('source')
def source():
    """Open the project root directory in Neovim (alias for 'open').
    
    Launches Neovim with the project root directory
    (~/dev/reservation-tracking-sheets) as the working directory.
    
    \b
    Example:
      reservations source
    """
    # Call the open command
    ctx = click.get_current_context()
    ctx.invoke(open_cmd)
