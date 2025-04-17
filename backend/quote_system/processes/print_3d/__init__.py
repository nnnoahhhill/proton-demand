# processes/print_3d/__init__.py

# This file makes the 'print_3d' directory a Python sub-package.

from .processor import Print3DProcessor
from .slicer import SlicerResult
from .dfm_rules import (
    check_bounding_box,
    check_mesh_integrity,
    check_thin_walls,
    check_minimum_features,
    check_small_holes,
    check_contact_area_stability,
    check_overhangs_and_support,
    check_warping_risk,
    check_internal_voids_and_escape
)

# You can optionally define an __all__ list to control what 'from .print_3d import *' imports
__all__ = [
    "Print3DProcessor",
    "SlicerResult",
    "check_bounding_box",
    "check_mesh_integrity",
    "check_thin_walls",
    "check_minimum_features",
    "check_small_holes",
    "check_contact_area_stability",
    "check_overhangs_and_support",
    "check_warping_risk",
    "check_internal_voids_and_escape"
] 