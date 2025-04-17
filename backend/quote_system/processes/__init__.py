# processes/__init__.py

# This file makes the 'processes' directory a Python package.
# Keep it simple - imports are handled by the modules that need them.

# No code needed here for basic package structure.

# If a factory function is desired later, it should be corrected like this:
# from typing import Type, Dict
# import logging
# from core.common_types import ManufacturingProcess # Absolute import
# from .base_processor import BaseProcessor
# from .print_3d.processor import Print3DProcessor
# try:
#     from .cnc.processor import CncProcessor
#     cnc_available = True
# except ImportError:
#     CncProcessor = None # Define as None if import fails
#     cnc_available = False
#
# logger = logging.getLogger(__name__)
#
# PROCESSOR_MAP: Dict[ManufacturingProcess, Type[BaseProcessor]] = {
#     ManufacturingProcess.PRINT_3D: Print3DProcessor,
#     **( {ManufacturingProcess.CNC: CncProcessor} if cnc_available and CncProcessor else {} )
# }
#
# def get_processor_factory(process_type: ManufacturingProcess, markup: float) -> BaseProcessor:
#     """Factory function to instantiate the correct processor."""
#     processor_class = PROCESSOR_MAP.get(process_type)
#     if not processor_class:
#         raise NotImplementedError(f"No processor for {process_type}")
#     return processor_class(markup=markup) # Pass markup

# Expose key submodules
from . import print_3d
from . import cnc
# from . import sheet_metal # Uncomment when available

# Import commonly-used items from submodules for convenience
from .print_3d import Print3DProcessor
from .cnc import CncProcessor
# from .sheet_metal import SheetMetalProcessor # Uncomment when available

# Define what gets imported with 'from quote_system.processes import *'
__all__ = [
    "print_3d",
    "cnc",
    # "sheet_metal",  # Uncomment when available
    "Print3DProcessor",
    "CncProcessor",
    # "SheetMetalProcessor",  # Uncomment when available
]