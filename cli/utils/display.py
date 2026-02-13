"""Display utilities for consistent CLI output formatting."""

import click


def success(message: str) -> None:
    """Display success message with green checkmark.
    
    Args:
        message: Success message to display
    """
    click.echo(click.style(f"✅ {message}", fg="green"))


def error(message: str) -> None:
    """Display error message with red X.
    
    Args:
        message: Error message to display
    """
    click.echo(click.style(f"❌ {message}", fg="red"))


def info(message: str) -> None:
    """Display info message with cyan color.
    
    Args:
        message: Info message to display
    """
    click.echo(click.style(f"ℹ️  {message}", fg="cyan"))


def warning(message: str) -> None:
    """Display warning message with yellow color.
    
    Args:
        message: Warning message to display
    """
    click.echo(click.style(f"⚠️  {message}", fg="yellow"))


def section_header(title: str) -> None:
    """Display formatted section header.
    
    Args:
        title: Section title to display
    """
    click.echo("\n" + "="*70)
    click.echo(click.style(f"  {title}", bold=True))
    click.echo("="*70)
