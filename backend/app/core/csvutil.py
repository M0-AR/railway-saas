"""CSV output helpers.

Spreadsheet applications treat cells beginning with =, +, -, @, tab or a
line break as formulas or external references. Prefixing untrusted values
with a single quote keeps the exported data inert (OWASP ASVS 5.0 V1.2.10).
"""

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def csv_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(_DANGEROUS_PREFIXES):
        return "'" + value
    return value
