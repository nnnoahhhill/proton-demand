# testing/conftest.py

import pytest
from pathlib import Path
import logging
import sys

# Ensure trimesh is imported at the top level
try:
    import trimesh
except ImportError:
    pytest.fail("Trimesh library not found.", pytrace=False)

# --- Project Imports (Use absolute paths from root) ---
# Define placeholders first
CncProcessor = None
Print3DProcessor = None
settings = None
geometry = None
ManufacturingProcess = None
MaterialInfo = None
Print3DTechnology = None
cnc_available = False
print3d_available = False

try:
    from core import geometry
    from core.common_types import ManufacturingProcess, MaterialInfo, Print3DTechnology
    from processes.print_3d.processor import Print3DProcessor
    print3d_available = True
except ImportError as e:
     print(f"[conftest.py] CRITICAL Error importing core/3D print modules: {e}")
     pytest.fail(f"Failed to import essential project modules: {e}", pytrace=False)

try:
    from processes.cnc.processor import CncProcessor
    cnc_available = True
except ImportError:
    print("[conftest.py] INFO: CNC Processor module not found. CNC tests will be skipped.")
    cnc_available = False
    CncProcessor = None

try:
    from config import settings
except ImportError as e:
     print(f"[conftest.py] CRITICAL Error importing config module: {e}")
     pytest.fail(f"Failed to import config module: {e}", pytrace=False)

logger = logging.getLogger(__name__)
BENCHMARK_DIR = Path(__file__).parent / "benchmark_models"

# --- Fixtures ---

@pytest.fixture(scope="session")
def load_test_model():
    _cache = {}
    def _loader(filename: str) -> trimesh.Trimesh:
        # ... (loader implementation unchanged) ...
        if filename in _cache: return _cache[filename]
        file_path = BENCHMARK_DIR / filename
        if not file_path.exists(): pytest.fail(f"Test model not found: {file_path}. Run generate script.", pytrace=False)
        try:
            mesh = geometry.load_mesh(str(file_path))
            if not hasattr(mesh, 'metadata'): mesh.metadata = {}
            mesh.metadata['file_name'] = filename
            _cache[filename] = mesh
            logger.debug(f"Loaded test model: {filename}")
            return mesh
        except Exception as e: pytest.fail(f"Failed to load test model '{filename}': {e}", pytrace=False)
    return _loader

@pytest.fixture(scope="session")
def print3d_processor() -> Print3DProcessor:
    if not print3d_available or Print3DProcessor is None: pytest.skip("Skipping 3D Print tests.")
    try: return Print3DProcessor(markup=settings.markup_factor)
    except Exception as e: pytest.fail(f"Failed to initialize Print3DProcessor: {e}", pytrace=False)

@pytest.fixture(scope="session")
def cnc_processor() -> CncProcessor:
    if not cnc_available or CncProcessor is None: pytest.skip("Skipping CNC tests.")
    try: return CncProcessor(markup=settings.markup_factor)
    except Exception as e: pytest.fail(f"Failed to initialize CncProcessor: {e}", pytrace=False)

@pytest.fixture(scope="module")
def sla_material_info(print3d_processor: Print3DProcessor) -> MaterialInfo:
    try: return print3d_processor.get_material_info("sla_resin_standard")
    except Exception as e: pytest.fail(f"Failed to get sla_resin_standard: {e}")
@pytest.fixture(scope="module")
def fdm_material_info(print3d_processor: Print3DProcessor) -> MaterialInfo:
     try: return print3d_processor.get_material_info("fdm_pla_standard")
     except Exception as e: pytest.fail(f"Failed to get fdm_pla_standard: {e}")
@pytest.fixture(scope="module")
def sls_material_info(print3d_processor: Print3DProcessor) -> MaterialInfo:
    try: return print3d_processor.get_material_info("sls_nylon12_white")
    except Exception as e: pytest.fail(f"Failed to get sls_nylon12_white: {e}")

# --- Explicit Model Fixtures ---
# Define all fixtures explicitly to avoid potential discovery issues

@pytest.fixture(scope="session")
def pass_cube_10mm(load_test_model) -> trimesh.Trimesh: return load_test_model("pass_cube_10mm.stl")
@pytest.fixture(scope="session")
def pass_cube_50mm(load_test_model) -> trimesh.Trimesh: return load_test_model("pass_cube_50mm.stl")
@pytest.fixture(scope="session")
def pass_high_poly_sphere(load_test_model) -> trimesh.Trimesh: return load_test_model("pass_high_poly_sphere.stl")
@pytest.fixture(scope="session")
def pass_low_poly_sphere(load_test_model) -> trimesh.Trimesh: return load_test_model("pass_low_poly_sphere.stl")
@pytest.fixture(scope="session")
def fail_thin_wall_0_1mm(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_thin_wall_0.1mm.stl")
@pytest.fixture(scope="session")
def fail_non_manifold_edge(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_non_manifold_edge.stl")
@pytest.fixture(scope="session")
def fail_multi_shell(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_multi_shell.stl")
@pytest.fixture(scope="session")
def fail_mesh_with_hole(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_mesh_with_hole.stl")
@pytest.fixture(scope="session")
def fail_non_manifold_vertex(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_non_manifold_vertex.stl")
@pytest.fixture(scope="session")
def fail_tiny_cube_0_1mm(load_test_model) -> trimesh.Trimesh: return load_test_model("fail_tiny_cube_0.1mm.stl")
@pytest.fixture(scope="session")
def warn_thin_wall_0_5mm(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_thin_wall_0.5mm.stl")
# --- FIX: Explicitly define warn_hole fixture ---
@pytest.fixture(scope="session")
def warn_hole(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_hole.stl")
# --- END FIX ---
@pytest.fixture(scope="session")
def warn_overhang_bridge(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_overhang_bridge.stl")
@pytest.fixture(scope="session")
def warn_internal_void(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_internal_void.stl")
@pytest.fixture(scope="session")
def warn_knife_edge_5deg(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_knife_edge_5deg.stl")
@pytest.fixture(scope="session")
def warn_large_cube_300mm(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_large_cube_300mm.stl")
@pytest.fixture(scope="session")
def warn_min_contact_sphere(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_min_contact_sphere.stl")
@pytest.fixture(scope="session")
def warn_sharp_spikes(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_sharp_spikes.stl")
@pytest.fixture(scope="session")
def warn_small_hole_0_2mm(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_small_hole_0.2mm.stl")
@pytest.fixture(scope="session")
def warn_tall_pillar_h50_r0_5(load_test_model) -> trimesh.Trimesh: return load_test_model("warn_tall_pillar_h50_r0.5.stl")