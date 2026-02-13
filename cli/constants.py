"""Constants used throughout the CLI application."""

# Month name translations
MONTH_NAMES = {
    'january': {'en': 'January', 'es': 'Enero'},
    'february': {'en': 'February', 'es': 'Febrero'},
    'march': {'en': 'March', 'es': 'Marzo'},
    'april': {'en': 'April', 'es': 'Abril'},
    'may': {'en': 'May', 'es': 'Mayo'},
    'june': {'en': 'June', 'es': 'Junio'},
    'july': {'en': 'July', 'es': 'Julio'},
    'august': {'en': 'August', 'es': 'Agosto'},
    'september': {'en': 'September', 'es': 'Septiembre'},
    'october': {'en': 'October', 'es': 'Octubre'},
    'november': {'en': 'November', 'es': 'Noviembre'},
    'december': {'en': 'December', 'es': 'Diciembre'}
}

# Month abbreviations
MONTH_ABBREV = {
    'jan': 'january', 'feb': 'february', 'mar': 'march',
    'apr': 'april', 'may': 'may', 'jun': 'june',
    'jul': 'july', 'aug': 'august', 'sep': 'september',
    'oct': 'october', 'nov': 'november', 'dec': 'december'
}

# Month groups for convenience
MONTH_GROUPS = {
    'q1': ['jan', 'feb', 'mar'],
    'q2': ['apr', 'may', 'jun'],
    'q3': ['jul', 'aug', 'sep'],
    'q4': ['oct', 'nov', 'dec'],
    'all': ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
            'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
}
