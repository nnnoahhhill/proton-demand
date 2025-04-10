# core/geometry.py

import os
import tempfile
import logging
from typing import Optional, Tuple

import trimesh
import numpy as np
from trimesh.exchange.stl import load_stl

# Attempt to import OpenCASCADE for STEP support
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone, IFSelect_ItemsByEntity
    from OCC.Core.StlAPI import StlAPI_Writer
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    # from OCC.Display.SimpleGui import init_display # Used for OCC graphical init if needed elsewhere, but not directly here.
    STEP_SUPPORT = True
except ImportError:
    STEP_SUPPORT = False
    logging.warning(
        "pythonocc-core not found. STEP file support will be disabled. "
        "Install with 'conda install -c conda-forge pythonocc-core' or 'pip install pythonocc-core'."
    )

from core.common_types import MeshProperties, BoundingBox
from core.exceptions import FileFormatError, GeometryProcessingError, StepConversionError

logger = logging.getLogger(__name__)

# Default meshing quality for STEP to STL conversion
DEFAULT_MESHING_DEFLECTION = 0.05 # Smaller value = finer mesh, potentially slower conversion

def load_mesh(file_path: str) -> trimesh.Trimesh:
    """
    Loads a mesh from STL or STEP file. Converts STEP to a temporary STL first.

    Args:
        file_path: Path to the input file (.stl, .step, .stp).

    Returns:
        A Trimesh object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        FileFormatError: If the file extension is unsupported.
        StepConversionError: If STEP conversion fails.
        GeometryProcessingError: If Trimesh fails to load the mesh.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()

    logger.info(f"Loading mesh from: {file_name} (Extension: {file_ext})")

    mesh = None
    temp_stl_file = None

    try:
        if file_ext == ".stl":
            try:
                # Use Trimesh's robust STL loader
                # file_obj needs to be opened in 'rb' mode for Trimesh
                with open(file_path, 'rb') as f:
                    mesh = trimesh.load(f, file_type='stl')
                logger.info(f"Successfully loaded STL file: {file_name}")
            except Exception as e:
                logger.error(f"Trimesh failed to load STL '{file_name}': {e}", exc_info=True)
                # Sometimes direct loading fails, try the specific loader
                try:
                    with open(file_path, 'rb') as f:
                        mesh_data = load_stl(f)
                        mesh = trimesh.Trimesh(**mesh_data)
                    logger.info(f"Successfully loaded STL file using specific loader: {file_name}")
                except Exception as e_alt:
                     logger.error(f"Trimesh specific STL loader also failed for '{file_name}': {e_alt}", exc_info=True)
                     raise GeometryProcessingError(f"Failed to load STL file '{file_name}': {e_alt}") from e_alt

        elif file_ext in [".step", ".stp"]:
            if not STEP_SUPPORT:
                raise FileFormatError(
                    "STEP file format requires 'pythonocc-core'. Please install it."
                )
            logger.info(f"STEP file detected. Converting '{file_name}' to STL...")
            temp_stl_file = _convert_step_to_stl(file_path)
            if temp_stl_file:
                try:
                    with open(temp_stl_file, 'rb') as f:
                         mesh = trimesh.load(f, file_type='stl')
                    logger.info(f"Successfully converted STEP and loaded temporary STL for: {file_name}")
                except Exception as e:
                    logger.error(f"Trimesh failed to load temporary STL from STEP '{file_name}': {e}", exc_info=True)
                    raise GeometryProcessingError(f"Failed to load mesh from converted STEP file '{file_name}': {e}") from e
            else:
                # _convert_step_to_stl would have raised StepConversionError
                raise StepConversionError(f"STEP to STL conversion failed for '{file_name}'.") # Should not happen if _convert handles errors

        else:
            raise FileFormatError(f"Unsupported file format: '{file_ext}'. Use STL, STEP, or STP.")

        # Post-load validation
        if not isinstance(mesh, trimesh.Trimesh):
             raise GeometryProcessingError(f"Loaded object from '{file_name}' is not a Trimesh instance.")
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
             raise GeometryProcessingError(f"Mesh loaded from '{file_name}' has no vertices or faces. It might be empty or corrupted.")

        return mesh

    finally:
        # Clean up temporary STL file if created
        if temp_stl_file and os.path.exists(temp_stl_file):
            try:
                os.unlink(temp_stl_file)
                logger.debug(f"Removed temporary STL file: {temp_stl_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary STL file '{temp_stl_file}': {e}")

def _convert_step_to_stl(step_file_path: str, deflection: float = DEFAULT_MESHING_DEFLECTION) -> Optional[str]:
    """
    Converts a STEP file to a temporary STL file using pythonocc-core.

    Args:
        step_file_path: Path to the input STEP file.
        deflection: Meshing deflection parameter (controls mesh quality).

    Returns:
        Path to the created temporary STL file, or None if conversion fails.

    Raises:
        StepConversionError: If any part of the OCC conversion process fails.
    """
    if not STEP_SUPPORT:
        raise StepConversionError("Cannot convert STEP file: pythonocc-core is not installed.")

    temp_stl_path = None
    try:
        # Create a temporary file for the STL output
        # delete=False is important so Trimesh can open it by path later
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as temp_stl_file:
            temp_stl_path = temp_stl_file.name
        logger.debug(f"Created temporary STL path: {temp_stl_path}")

        # --- OCC STEP Reading ---
        step_reader = STEPControl_Reader()
        status = step_reader.ReadFile(step_file_path)

        if status != IFSelect_RetDone:
            # Try to get more specific error info if possible
            fail_reason = "Unknown error"
            if status == 1: fail_reason = "Not Found"
            elif status == 2: fail_reason = "Permission Denied"
            elif status == 3: fail_reason = "Open Error"
            elif status == 4: fail_reason = "Read Error"
            elif status == 5: fail_reason = "Format Error"
            # Add more specific status codes if known for OCC
            raise StepConversionError(f"OCC failed to read STEP file '{os.path.basename(step_file_path)}'. Status: {status} ({fail_reason})")

        # --- OCC Transfer Roots ---
        # Fetches the roots of the graph (usually the main shapes)
        # Use TransferRoots for automatic selection or loop nbroots/transfer if needed
        transfer_status = step_reader.TransferRoots()
        if not transfer_status:
             num_roots = step_reader.NbRootsForTransfer()
             if num_roots == 0:
                  raise StepConversionError("OCC found no transferable roots (shapes) in the STEP file.")
             # Fallback: try transferring one by one if TransferRoots fails broadly
             transferred_any = False
             for i in range(1, num_roots + 1):
                  if step_reader.TransferRoot(i):
                       transferred_any = True
                       break # Usually only need one main shape
             if not transferred_any:
                 raise StepConversionError("OCC failed to transfer any root shapes from the STEP file.")


        # --- OCC Get Shape ---
        # Check number of shapes, handle assembly if needed (for now, assume single part)
        num_shapes = step_reader.NbShapes()
        if num_shapes == 0:
            raise StepConversionError("OCC transferred roots but resulted in zero shapes.")
        if num_shapes > 1:
            logger.warning(f"STEP file contains multiple shapes ({num_shapes}). Processing the first shape.")
            # Future enhancement: Could process all, combine them, or handle assemblies.

        shape = step_reader.Shape(1) # Get the first shape
        if shape.IsNull():
             raise StepConversionError("OCC resulted in a null shape after transfer.")

        # --- OCC Meshing ---
        logger.debug(f"Meshing shape with deflection: {deflection}")
        # BRepMesh_IncrementalMesh is commonly used for visualization/export meshes
        # Parameters: shape, linear deflection, is_relative, angular_deflection, parallel
        mesh_util = BRepMesh_IncrementalMesh(shape, deflection, False, 0.5, True) # Using relative deflection=False, ang_deflection=0.5, parallel=True
        mesh_util.Perform() # Perform the meshing algorithm

        if not mesh_util.IsDone():
            raise StepConversionError("OCC BRepMesh meshing algorithm failed to complete.")

        # --- OCC STL Writing ---
        stl_writer = StlAPI_Writer()
        stl_writer.SetASCIIMode(False) # Binary STL is generally preferred (smaller, faster)

        # Write the mesh associated with the shape to the STL file
        write_status = stl_writer.Write(shape, temp_stl_path)

        if not write_status:
            raise StepConversionError("OCC StlAPI_Writer failed to write the mesh to the temporary STL file.")

        # --- Final Check ---
        if not os.path.exists(temp_stl_path) or os.path.getsize(temp_stl_path) == 0:
             raise StepConversionError(f"Temporary STL file '{temp_stl_path}' was not created or is empty after OCC conversion.")

        logger.info(f"Successfully converted STEP '{os.path.basename(step_file_path)}' to temporary STL: {temp_stl_path}")
        return temp_stl_path

    except Exception as e:
        # Clean up the temp file if it exists and an error occurred
        if temp_stl_path and os.path.exists(temp_stl_path):
            try:
                os.unlink(temp_stl_path)
            except Exception as unlink_e:
                logger.warning(f"Failed to remove temporary STL file '{temp_stl_path}' during error handling: {unlink_e}")
        # Re-raise as a StepConversionError for consistent error handling upstream
        if isinstance(e, StepConversionError):
             raise # Keep the specific OCC error if already raised
        else:
             logger.error(f"Unexpected error during STEP conversion: {e}", exc_info=True)
             raise StepConversionError(f"Unexpected error during STEP conversion: {e}") from e

    # Should not be reached if errors are handled properly
    return None


def get_mesh_properties(mesh: trimesh.Trimesh) -> MeshProperties:
    """
    Extracts basic properties from a Trimesh object.

    Args:
        mesh: The input Trimesh object.

    Returns:
        A MeshProperties object.

    Raises:
        GeometryProcessingError: If essential properties cannot be calculated.
    """
    try:
        # Ensure calculations are done (Trimesh caches properties)
        vol = mesh.volume
        area = mesh.area
        bounds = mesh.bounds
        is_watertight = mesh.is_watertight

        if bounds is None:
             logger.warning("Could not determine mesh bounds.")
             min_coords = max_coords = np.array([0.0, 0.0, 0.0])
        else:
             min_coords = bounds[0]
             max_coords = bounds[1]

        size = max_coords - min_coords

        # Convert units assuming input is mm (common for STL/STEP)
        # Volume: mm^3 to cm^3 (divide by 1000)
        # Area: mm^2 to cm^2 (divide by 100)
        volume_cm3 = vol / 1000.0
        surface_area_cm2 = area / 100.0

        bbox = BoundingBox(
            min_x=min_coords[0], min_y=min_coords[1], min_z=min_coords[2],
            max_x=max_coords[0], max_y=max_coords[1], max_z=max_coords[2],
            size_x=size[0], size_y=size[1], size_z=size[2]
        )

        return MeshProperties(
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            bounding_box=bbox,
            volume_cm3=volume_cm3,
            surface_area_cm2=surface_area_cm2,
            is_watertight=is_watertight,
            units="mm" # Assuming mm units, might need refinement if units can vary
        )
    except Exception as e:
        logger.error(f"Failed to extract mesh properties: {e}", exc_info=True)
        raise GeometryProcessingError(f"Failed to calculate mesh properties: {e}") from e

def repair_mesh(mesh: trimesh.Trimesh, repair_level: str = "basic") -> trimesh.Trimesh:
    """
    Attempts to repair common mesh issues using Trimesh.

    Args:
        mesh: The input Trimesh object.
        repair_level: "basic" (remove duplicates, fix normals) or
                      "fill" (basic + fill holes).

    Returns:
        A potentially repaired Trimesh object. Might be the same object if no changes.
    """
    logger.info(f"Attempting '{repair_level}' mesh repair...")
    original_v = len(mesh.vertices)
    original_f = len(mesh.faces)

    try:
        # Basic repairs
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()
        mesh.remove_degenerate_faces()
        mesh.fix_normals(multibody=True) # Fix face winding

        if repair_level == "fill":
             # Fill holes - This can sometimes create undesirable geometry or fail
             try:
                 mesh.fill_holes()
                 # Check if it became watertight after filling
                 if mesh.is_watertight:
                      logger.info("Mesh became watertight after fill_holes.")
                 else:
                      logger.warning("Mesh fill_holes executed but mesh is still not watertight.")
             except Exception as e:
                 logger.warning(f"Trimesh fill_holes failed: {e}. Continuing with basic repairs.")

        # Check if repairs changed anything
        repaired_v = len(mesh.vertices)
        repaired_f = len(mesh.faces)
        if repaired_v != original_v or repaired_f != original_f:
             logger.info(f"Mesh repair modified geometry: Verts {original_v}->{repaired_v}, Faces {original_f}->{repaired_f}")
        else:
             logger.info("Mesh repair did not significantly alter geometry.")

        return mesh

    except Exception as e:
        logger.error(f"Error during Trimesh repair: {e}", exc_info=True)
        # Return the original mesh if repair fails catastrophically
        return mesh 