# This file makes the 'scrapers' directory a Python package.

try:
    from . import reuters
except Exception:
    reuters = None  # type: ignore

try:
    from . import bloomberg
except Exception:
    bloomberg = None  # type: ignore
