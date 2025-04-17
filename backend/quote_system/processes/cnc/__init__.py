# processes/cnc/__init__.py

# This file makes the 'cnc' directory a Python sub-package.

from .processor import CncProcessor

# You can optionally define an __all__ list to control what 'from .cnc import *' imports
__all__ = [
    "CncProcessor"
] 