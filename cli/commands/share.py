"""Share command - Display the service account email for Google Sheets sharing."""

import json
import sys

import click

from .. import PROJECT_ROOT
from ..utils.display import error, info


CREDENTIALS_PATH = PROJECT_ROOT / "credentials" / "service_account.json"


@click.command()
def share():
    """Display the service account email to share Google Sheets with.

    Reads the client_email from credentials/service_account.json and
    displays it so you can easily copy and share your Google Sheet
    with the service account.

    \b
    Usage:
      reservations share

    \b
    Then in Google Sheets:
      1. Click Share
      2. Paste the displayed email
      3. Grant Editor access
      4. Uncheck "Notify people"
      5. Click Share
    """
    try:
        with open(CREDENTIALS_PATH, "r") as f:
            credentials = json.load(f)
    except FileNotFoundError:
        error(f"Credentials file not found: {CREDENTIALS_PATH}")
        error("Download your service account key from Google Cloud Console")
        error("and save it as credentials/service_account.json")
        sys.exit(1)
    except json.JSONDecodeError:
        error(f"Invalid JSON in credentials file: {CREDENTIALS_PATH}")
        sys.exit(1)

    email = credentials.get("client_email")
    if not email:
        error("No 'client_email' field found in credentials file")
        sys.exit(1)

    info("Share your Google Sheet with this email (Editor access):\n")
    click.echo(click.style(f"  {email}", bold=True))
    click.echo()
