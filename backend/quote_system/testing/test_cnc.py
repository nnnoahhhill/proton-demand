# testing/test_cnc.py

import pytest
import trimesh
from pathlib import Path

# Project Imports
from quote_system.core.common_types import ManufacturingProcess, QuoteResult, DFMStatus, MaterialInfo, CNCTechnology
from quote_system.core.exceptions import MaterialNotFoundError
from quote_system.processes.cnc.processor import CncProcessor
from quote_system.config import settings

# --- Fixtures (Imported from conftest.py) ---
# cnc_processor
# pass_cube_10mm, pass_cube_50mm etc.

# --- Test Cases ---

# Example CNC material (assuming it exists in cnc_materials.json or equivalent)
@pytest.fixture(scope="module")
def aluminum_6061() -> MaterialInfo:
     return MaterialInfo(id="cnc-aluminum-6061", name="Aluminum 6061", process="CNC Machining",
                         technology=CNCTechnology.MILLING, density_g_cm3=2.70)


def test_cnc_quote_success_pass_cube(pass_cube_10mm: trimesh.Trimesh, cnc_processor: CncProcessor, aluminum_6061: MaterialInfo):
    """Tests generating a CNC quote for a simple, valid model."""
    # Use absolute path
    file_path = Path(__file__).parent / "benchmark_models" / "pass_cube_10mm.stl"
    material_id = aluminum_6061.id # Use the ID from the fixture

    try:
        result: QuoteResult = cnc_processor.generate_quote(
            file_path=str(file_path),
            material_id=material_id
        )

        assert result is not None
        assert isinstance(result, QuoteResult)
        assert result.process == ManufacturingProcess.CNC
        assert result.material_info.id == material_id
        # Basic CNC DFM might just check bounding box or complexity for now
        assert result.dfm_report.status == DFMStatus.PASS # Expect basic pass for simple cube
        assert result.cost_estimate is not None
        assert result.customer_price > 0
        assert result.base_cost > 0
        assert result.customer_price >= result.base_cost * settings.markup_factor
        assert result.processing_time_sec > 0
        assert result.quote_id is not None
        # CNC might not have a simple 'process time string' like 3DP
        # assert result.estimated_process_time_str is not None

    except MaterialNotFoundError:
        pytest.skip(f"Material ID '{material_id}' not found. Skipping test.")
    except Exception as e:
         pytest.fail(f"CNC Quote generation failed unexpectedly: {e}")

def test_cnc_quote_material_not_found(pass_cube_10mm: trimesh.Trimesh, cnc_processor: CncProcessor):
    """Tests CNC quote generation with an invalid material ID."""
    file_path = Path(__file__).parent / "benchmark_models" / "pass_cube_10mm.stl"
    invalid_material_id = "non-existent-cnc-material-xyz"

    with pytest.raises(MaterialNotFoundError):
        cnc_processor.generate_quote(str(file_path), invalid_material_id)

# --- DFM Specific Tests (If applicable for CNC) ---
# Example: If CNC has a max size DFM check
# def test_cnc_dfm_fail_too_large(...):
#     ... DFM check logic ...

# Add more tests:
# - Test with STEP files (often preferred for CNC)
# - Test models requiring different CNC operations (milling vs turning if supported)
# - Test models with features that might increase complexity/cost (e.g., deep pockets, small details)
# - Test DFM rules specific to CNC (e.g., minimum corner radius, maximum aspect ratio for features) 