"""
ProtoGo DFM (Design for Manufacturing) analysis package.

This package provides analysis tools for multiple manufacturing methods:
- 3D Printing (SLA, FDM, SLS)
- CNC Machining

Main modules:
- 3d-print-dfm-analyzer: 3D printing analysis
- cnc-feature-extraction: CNC feature recognition
- cnc-quoting-system: CNC cost estimation
- manufacturing-dfm-api: Unified API for all methods
"""

import os
import sys
import importlib.util
from pathlib import Path

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import 3D printing DFM analyzer
try:
    # Using importlib to handle module names with dashes
    spec = importlib.util.spec_from_file_location(
        "3d_print_dfm_analyzer",
        os.path.join(current_dir, "3d-print-dfm-analyzer.py")
    )
    if spec is not None:
        dfm_analyzer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dfm_analyzer_module)
        DFMAnalyzer = dfm_analyzer_module.DFMAnalyzer
        DEFAULT_CONFIG = dfm_analyzer_module.DEFAULT_CONFIG
except ImportError as e:
    print(f"Error importing 3D printing DFM analyzer: {e}")
except Exception as e:
    print(f"Unexpected error importing 3D printing DFM analyzer: {e}")

# Import CNC modules
try:
    # Load cnc-quoting-system.py
    spec = importlib.util.spec_from_file_location(
        "cnc_quoting_system",
        os.path.join(current_dir, "cnc-quoting-system.py")
    )
    cnc_quoting_system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cnc_quoting_system)

    # Load cnc-feature-extraction.py
    spec = importlib.util.spec_from_file_location(
        "cnc_feature_extraction",
        os.path.join(current_dir, "cnc-feature-extraction.py")
    )
    cnc_feature_extraction = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cnc_feature_extraction)

    # Export the classes
    CNCQuoteAnalyzer = cnc_quoting_system.CNCQuoteAnalyzer
    CNCFeatureRecognition = cnc_feature_extraction.CNCFeatureRecognition
    MATERIALS = cnc_quoting_system.MATERIALS
except ImportError as e:
    print(f"Error importing CNC modules: {e}")
except Exception as e:
    print(f"Unexpected error importing CNC modules: {e}")