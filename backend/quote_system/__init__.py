# quote_system/__init__.py

# This file makes the 'quote_system' directory a Python package.

# You can optionally import key modules to expose at package level
from . import core
from . import processes
from . import visualization

# Define what gets imported with 'from quote_system import *'
__all__ = [
    "core",
    "processes",
    "visualization"
] 