# testing/test_3d_print_quote.py

import pytest
import trimesh
from pathlib import Path

# Project Imports (Standardized)
from quote_system.core.common_types import ManufacturingProcess, QuoteResult, DFMStatus, MaterialInfo, Print3DTechnology
from quote_system.core.exceptions import MaterialNotFoundError, ConfigurationError
from quote_system.processes.print_3d.processor import Print3DProcessor
from quote_system.config import settings

# --- Fixtures (Imported from conftest.py) ---
# print3d_processor, sla_material_info, fdm_material_info
# pass_cube_10mm, fail_non_manifold_edge, etc.

# --- Test Cases ---

# Use a known good model and valid material for basic quote success test
def test_quote_success_pass_cube_sla(pass_cube_10mm: trimesh.Trimesh, print3d_processor: Print3DProcessor):
    """Tests generating a quote for a valid model and SLA material."""
    # Use absolute path to avoid issues with CWD during testing
    file_path = Path(__file__).parent / "benchmark_models" / "pass_cube_10mm.stl"
    material_id = "sla_resin_standard" # Corrected ID

    try:
        result: QuoteResult = print3d_processor.generate_quote(
            file_path=str(file_path),
            material_id=material_id
        )

        assert result is not None
        assert isinstance(result, QuoteResult)
        assert result.process == ManufacturingProcess.PRINT_3D
        assert result.material_info.id == material_id
        assert result.dfm_report.status == DFMStatus.PASS
        assert result.cost_estimate is not None
        assert result.customer_price > 0
        assert result.base_cost > 0
        assert result.customer_price >= result.base_cost * settings.markup_factor
        assert result.processing_time_sec > 0
        assert result.quote_id is not None
        assert result.estimated_process_time_str is not None # Check slicer output was parsed

    except MaterialNotFoundError:
        pytest.skip(f"Material ID '{material_id}' not found. Skipping test.")
    except ConfigurationError as e:
        if "Slicer executable not found" in str(e):
             pytest.skip(f"PrusaSlicer not found or configured: {e}. Skipping test.")
        else:
             pytest.fail(f"Unexpected ConfigurationError: {e}")
    except Exception as e:
         pytest.fail(f"Quote generation failed unexpectedly: {e}")

def test_quote_success_pass_cube_fdm(pass_cube_10mm: trimesh.Trimesh, print3d_processor: Print3DProcessor):
    """Tests generating a quote for a valid model and FDM material."""
    file_path = Path(__file__).parent / "benchmark_models" / "pass_cube_10mm.stl"
    material_id = "fdm_pla_standard" # Corrected ID (assuming a base PLA exists)

    try:
        result: QuoteResult = print3d_processor.generate_quote(
            file_path=str(file_path),
            material_id=material_id
        )
        assert result.process == ManufacturingProcess.PRINT_3D
        assert result.material_info.id == material_id
        assert result.dfm_report.status == DFMStatus.PASS
        assert result.cost_estimate is not None
        assert result.customer_price > 0

    except MaterialNotFoundError:
        pytest.skip(f"Material ID '{material_id}' not found. Skipping test.")
    except ConfigurationError as e:
        if "Slicer executable not found" in str(e):
             pytest.skip(f"PrusaSlicer not found or configured: {e}. Skipping test.")
        else:
             pytest.fail(f"Unexpected ConfigurationError: {e}")
    except Exception as e:
         pytest.fail(f"Quote generation failed unexpectedly: {e}")


def test_quote_dfm_fail_non_manifold(fail_non_manifold_edge: trimesh.Trimesh, print3d_processor: Print3DProcessor):
    """Tests quote generation for a model that should fail DFM."""
    file_path = Path(__file__).parent / "benchmark_models" / "fail_non_manifold_edge.stl"
    material_id = "sla_resin_standard" # Use a valid ID, DFM should fail regardless

    try:
        result: QuoteResult = print3d_processor.generate_quote(str(file_path), material_id)
        assert result.dfm_report.status == DFMStatus.FAIL
        assert result.cost_estimate is None # Costing should not run if DFM fails critically
        assert result.customer_price is None # Changed from 0.0 to None as per QuoteResult definition
        assert result.estimated_process_time_str is None

    except MaterialNotFoundError:
         pytest.skip(f"Material ID '{material_id}' not found. Skipping test.")
    # Don't expect slicer config error here as DFM runs first
    except Exception as e:
         pytest.fail(f"Quote generation failed unexpectedly: {e}")


def test_quote_material_not_found(pass_cube_10mm: trimesh.Trimesh, print3d_processor: Print3DProcessor):
    """Tests quote generation with an invalid material ID returns FAIL status and error message."""
    file_path = Path(__file__).parent / "benchmark_models" / "pass_cube_10mm.stl"
    invalid_material_id = "non-existent-material-123"

    # The generate_quote method catches MaterialNotFoundError internally
    result: QuoteResult = print3d_processor.generate_quote(str(file_path), invalid_material_id)

    assert result is not None
    assert result.dfm_report is not None
    assert result.dfm_report.status == DFMStatus.FAIL
    assert result.error_message is not None
    assert invalid_material_id in result.error_message
    assert "not available" in result.error_message
    assert result.cost_estimate is None
    assert result.customer_price is None

# Add more tests:
# - Models with DFM warnings (should still get a quote)
# - Test with different slicer profiles if applicable
# - Test boundary conditions for cost calculation (e.g., very small/large models)
# - Test quote with STEP/STP files if geometry loading supports them 