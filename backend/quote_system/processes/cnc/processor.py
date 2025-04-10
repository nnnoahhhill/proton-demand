import time
import logging
import os
from typing import List

import trimesh

from core.common_types import (
    ManufacturingProcess,
    MaterialInfo,
    MeshProperties,
    DFMReport,
    CostEstimate
)
# from quote_system.processes.base_processor import BaseProcessor
from processes.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

# ... rest of the file ... 