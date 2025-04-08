# processes/__init__.py

# This file makes the 'processes' directory a Python package.
# You can optionally add imports here to expose parts of the submodules directly,
# e.g., from .print_3d.processor import Print3DProcessor

# Or define a factory function to get the correct processor based on type.

from typing import Type, Optional, Dict
import logging

from ..core.common_types import ProcessType, AnalysisConfig
from .base_processor import BaseProcessor
from .print_3d.processor import Print3DProcessor
# Import other processors as they are added
# from .cnc_milling.processor import CNCMillingProcessor
# from .sheet_metal.processor import SheetMetalProcessor

logger = logging.getLogger(__name__)

# Map ProcessType enum to the corresponding processor class
PROCESSOR_MAP: Dict[ProcessType, Type[BaseProcessor]] = {
    ProcessType.PRINT_3D: Print3DProcessor,
    # ProcessType.CNC_MILLING: CNCMillingProcessor,
    # ProcessType.SHEET_METAL: SheetMetalProcessor,
}

def get_processor(process_type: ProcessType, config: Optional[AnalysisConfig] = None) -> BaseProcessor:
    """Factory function to instantiate the correct processor based on ProcessType."""
    processor_class = PROCESSOR_MAP.get(process_type)
    if not processor_class:
        logger.error(f"No processor implementation found for process type: {process_type}")
        raise NotImplementedError(f"No processor implementation found for process type: {process_type}")

    logger.info(f"Instantiating processor for {process_type.name}")
    return processor_class(config) 