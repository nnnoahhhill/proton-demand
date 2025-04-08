# processes/print_3d/dfm_rules.py

import time
import logging
from typing import List, Dict, Any, Optional

import numpy as np
import trimesh
import pymeshlab

from ...core.common_types import (
    DFMIssue, DFMLevel, DFMIssueType, MeshProperties, MaterialInfo, Print3DTechnology,
    BoundingBox # Added BoundingBox
)
from ...core.exceptions import DFMCheckError

logger = logging.getLogger(__name__)

# --- Configuration Thresholds (Consider moving to a config file/object later) ---
CONFIG = {
    "min_wall_thickness_mm": { # Technology specific thresholds
        "FDM": 0.8, # Thicker nozzle/layer height for FDM
        "SLA": 0.4, # Can achieve finer details
        "SLS": 0.7
    },
    "critical_wall_thickness_factor": 0.6, # Walls below min * this factor are critical fail
    "warn_overhang_angle_deg": 45.0, # Standard angle where supports usually needed
    "error_overhang_angle_deg": 65.0, # Very steep angles, likely need robust support
    "min_feature_size_mm": 0.5,
    "max_shells_allowed": 1, # Strict: only allow one continuous part per file
    "large_flat_area_threshold_cm2": 50.0, # Threshold for potential warping warning
    "escape_hole_recommendation_threshold_cm3": 5.0, # Min volume for recommending escape holes
    "max_bounding_box_mm": {"x": 300, "y": 300, "z": 300} # Example build volume
}

# --- Helper Functions ---

def _get_threshold(key: str, tech: Print3DTechnology, default: float) -> float:
    """Safely get a threshold, falling back to default."""
    value = CONFIG.get(key)
    if isinstance(value, dict):
        # Use .name to get enum member name string for dict key lookup
        tech_name = tech.name if isinstance(tech, Print3DTechnology) else str(tech)
        return value.get(tech_name, default)
    elif isinstance(value, (int, float)):
        return value
    return default

# --- DFM Check Functions ---

def check_bounding_box(mesh_properties: MeshProperties) -> List[DFMIssue]:
    """Checks if the model fits within the maximum build volume."""
    issues = []
    max_dims = CONFIG["max_bounding_box_mm"]
    bbox = mesh_properties.bounding_box

    exceeded = []
    if bbox.size_x > max_dims["x"]: exceeded.append(f"X ({bbox.size_x:.1f}mm > {max_dims['x']}mm)")
    if bbox.size_y > max_dims["y"]: exceeded.append(f"Y ({bbox.size_y:.1f}mm > {max_dims['y']}mm)")
    if bbox.size_z > max_dims["z"]: exceeded.append(f"Z ({bbox.size_z:.1f}mm > {max_dims['z']}mm)")

    if exceeded:
        issues.append(DFMIssue(
            issue_type=DFMIssueType.BOUNDING_BOX_LIMIT,
            level=DFMLevel.CRITICAL,
            message=f"Model exceeds maximum build volume in dimensions: {', '.join(exceeded)}.",
            recommendation=f"Scale the model down or split it into multiple parts to fit within {max_dims['x']}x{max_dims['y']}x{max_dims['z']} mm."
        ))
    return issues

def check_mesh_integrity(ms: pymeshlab.MeshSet, mesh: trimesh.Trimesh, mesh_properties: MeshProperties) -> List[DFMIssue]:
    """Checks for critical mesh errors like non-manifold, multiple shells, negative volume."""
    issues = []
    start_time = time.time()

    # 1. Check for Negative Volume (Basic Sanity Check)
    if mesh_properties.volume_cm3 < 0:
        issues.append(DFMIssue(
            issue_type=DFMIssueType.GEOMETRY_ERROR,
            level=DFMLevel.CRITICAL,
            message=f"Model has negative volume ({mesh_properties.volume_cm3:.2f} cm³), indicating inverted normals or severe errors.",
            recommendation="Repair the mesh normals and ensure correct geometry orientation."
        ))
        # If volume is negative, other checks are likely unreliable
        return issues

    # 2. Non-Manifold Check (using PyMeshLab for robustness)
    try:
        # Ensure we have a mesh in the MeshSet
        if ms.mesh_id_exists(0):
            ms.set_current_mesh(0)
        else:
             # Attempt to add mesh if MeshSet is empty (e.g., if called directly)
             try:
                 ms.add_mesh(mesh, mesh.metadata.get('file_name', 'input_mesh'))
                 ms.set_current_mesh(0)
                 logger.warning("Mesh integrity check added mesh to MeshSet directly.")
             except Exception as add_err:
                 raise DFMCheckError(f"Failed to add mesh to MeshSet for integrity check: {add_err}")


        measures = ms.get_topological_measures()
        non_manifold_edges = measures.get('non_manifold_edges', 0)
        non_manifold_vertices = measures.get('non_manifold_vertices', 0)
        boundary_edges = measures.get('boundary_edges', 0) # Holes

        if non_manifold_edges > 0 or non_manifold_vertices > 0:
            issues.append(DFMIssue(
                issue_type=DFMIssueType.NON_MANIFOLD,
                level=DFMLevel.CRITICAL, # Often causes print failures
                message=f"Model is non-manifold ({non_manifold_edges} non-manifold edges, {non_manifold_vertices} non-manifold vertices). This often leads to print failures.",
                recommendation="Use mesh repair tools (e.g., Meshmixer, Blender, Netfabb) to fix non-manifold geometry and make the mesh watertight."
                # Visualization hint could be vertex/edge indices if PyMeshLab provides them easily, otherwise None
            ))
        elif boundary_edges > 0 and mesh_properties.is_watertight:
             # This is odd - Trimesh says watertight but PyMeshLab finds boundary edges? Log it.
              logger.warning(f"Mesh {mesh.metadata.get('file_name', '')} reported watertight by Trimesh but PyMeshLab found {boundary_edges} boundary edges.")
              # Could add a lower severity warning here if desired.
        elif boundary_edges > 0 and not mesh_properties.is_watertight:
             # This means there are holes in the mesh
              issues.append(DFMIssue(
                issue_type=DFMIssueType.NON_MANIFOLD, # Treat holes as non-manifold for printability
                level=DFMLevel.ERROR, # Usually repairable, but needs fixing
                message=f"Model has holes ({boundary_edges} boundary edges) and is not watertight.",
                recommendation="Use mesh repair tools to close holes and ensure the model is solid (watertight)."
            ))

    except Exception as e:
        logger.error(f"Error during PyMeshLab topological measures: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.GEOMETRY_ERROR,
            level=DFMLevel.ERROR, # Can't be sure it's critical
            message=f"Could not perform non-manifold check due to an analysis error: {e}",
            recommendation="Check mesh integrity manually or try repairing the mesh."
        ))
        # Allow continuing to other checks if this one fails

    # 3. Multiple Shells Check (Strict based on config)
    shell_count = -1 # Initialize
    try:
        # Count connected components using PyMeshLab's splitting filter
        # Create a copy to avoid modifying the original MeshSet state unintentionally
        temp_ms = pymeshlab.MeshSet()
        # Ensure the current mesh exists before adding
        if ms.mesh_id_exists(ms.current_mesh_id()):
             temp_ms.add_mesh(ms.current_mesh(), "temp_mesh_for_shells")
             split_info = temp_ms.generate_splitting_by_connected_components()
             # The split_info might return the number of new meshes created, or we check mesh_number
             shell_count = temp_ms.mesh_number() # Number of meshes after splitting
             del temp_ms # Clean up the temporary MeshSet
        else:
             logger.error("Cannot count shells: Current mesh ID does not exist in MeshSet.")
             shell_count = -1 # Indicate failure


        if shell_count > CONFIG["max_shells_allowed"]:
            issues.append(DFMIssue(
                issue_type=DFMIssueType.MULTIPLE_SHELLS,
                level=DFMLevel.CRITICAL, # As per user's strict requirement
                message=f"Model contains {shell_count} separate disconnected parts (shells). Only {CONFIG['max_shells_allowed']} shell(s) are allowed per file.",
                recommendation="Combine the parts into a single shell in your CAD software, or ensure they are correctly connected (e.g., by supports/base if intended)."
            ))
        elif shell_count == -1: # Check failed
             raise DFMCheckError("Shell count check failed internally.")

    except Exception as e:
        logger.error(f"Error during shell counting: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.GEOMETRY_ERROR,
            level=DFMLevel.WARN, # Unsure of the impact
            message=f"Could not reliably count separate shells due to an analysis error: {e}",
            recommendation="Manually verify the model consists of a single continuous part."
        ))

    logger.debug(f"Mesh integrity checks completed in {time.time() - start_time:.3f}s")
    return issues


def check_thin_walls(ms: pymeshlab.MeshSet, tech: Print3DTechnology) -> List[DFMIssue]:
    """
    Checks for thin walls using PyMeshLab's geometric measures (approximate).

    Args:
        ms: PyMeshLab MeshSet containing the mesh.
        tech: The specific 3D printing technology.

    Returns:
        List of DFMIssues related to thin walls.
    """
    issues = []
    start_time = time.time()
    min_thickness = _get_threshold("min_wall_thickness_mm", tech, 0.8)
    critical_thickness = min_thickness * CONFIG["critical_wall_thickness_factor"]
    logger.info(f"Checking for thin walls. Min threshold ({tech.name if isinstance(tech, Print3DTechnology) else tech}): {min_thickness:.2f}mm, Critical: {critical_thickness:.2f}mm")

    try:
        if not ms.mesh_id_exists(0):
             # This should not happen if called from processor, but handle defensively
             raise DFMCheckError("Mesh not found in MeshSet for thin wall check.")
        ms.set_current_mesh(0)

        # Use PyMeshLab filter to compute per-vertex thickness approximation
        # Note: This is an approximation and might not catch all thin walls perfectly.
        # 'compute_scalar_by_shape_diameter_function' seems promising but needs testing.
        # filter_name = "compute_scalar_by_shape_diameter_function"
        # try:
        #      ms.apply_filter(filter_name, approximate=True) # Check filter parameters
        # except pymeshlab.PyMeshLabException as filter_err:
        #      logger.error(f"PyMeshLab filter '{filter_name}' failed: {filter_err}")
        #      raise DFMCheckError(f"Filter '{filter_name}' execution failed.")

        # *** Placeholder Logic ***
        # As a temporary placeholder (since a direct, fast PyMeshLab thickness filter isn't obvious),
        # we'll issue a generic warning if this check is called, reminding that this needs implementation.
        logger.warning("Thin wall check implementation using PyMeshLab filter is incomplete/placeholder.")
        issues.append(DFMIssue(
             issue_type=DFMIssueType.THIN_WALL,
             level=DFMLevel.INFO,
             message="Thin wall check requires further implementation or integration with a specific thickness analysis method.",
             recommendation="Verify wall thicknesses manually based on design requirements and printer capabilities."
        ))
        # *** End Placeholder Logic ***

        # --- Ideal Logic (if a thickness filter providing per-vertex/face data exists) ---
        # 1. Run the PyMeshLab thickness filter: ms.apply_filter('some_thickness_filter', ...)
        # 2. Get the resulting per-vertex or per-face thickness values:
        #    if ms.current_mesh().has_vertex_quality():
        #        thickness_values = ms.current_mesh().vertex_quality_array()
        #    elif ms.current_mesh().has_face_quality(): # Less common for thickness
        #        thickness_values = ms.current_mesh().face_quality_array() # Need mapping to vertices if needed
        #    else:
        #        raise DFMCheckError("Thickness filter did not produce quality values.")
        # 3. Find vertices/faces below thresholds:
        #    critical_indices = np.where(thickness_values < critical_thickness)[0]
        #    error_indices = np.where((thickness_values >= critical_thickness) & (thickness_values < min_thickness))[0]
        # 4. Create DFMIssues based on findings:
        #    if len(critical_indices) > 0:
        #        issues.append(DFMIssue(
        #            issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.CRITICAL,
        #            message=f"Critically thin walls found (less than {critical_thickness:.2f}mm).",
        #            recommendation=f"Increase wall thickness significantly (target > {min_thickness:.2f}mm).",
        #            visualization_hint={"type": "vertex_indices", "indices": critical_indices.tolist()},
        #            details={"min_measured_critical": np.min(thickness_values[critical_indices])}
        #        ))
        #    if len(error_indices) > 0:
        #         issues.append(DFMIssue(
        #            issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.ERROR,
        #            message=f"Thin walls found (between {critical_thickness:.2f}mm and {min_thickness:.2f}mm).",
        #            recommendation=f"Increase wall thickness to at least {min_thickness:.2f}mm for reliable printing.",
        #            visualization_hint={"type": "vertex_indices", "indices": error_indices.tolist()},
        #            details={"min_measured_error": np.min(thickness_values[error_indices])}
        #        ))
        # --- End Ideal Logic ---

    except Exception as e:
        logger.error(f"Error during thin wall check: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.THIN_WALL,
            level=DFMLevel.WARN, # Unsure of severity if check fails
            message=f"Could not perform thin wall check due to an analysis error: {e}",
            recommendation="Manually verify minimum wall thicknesses meet requirements."
        ))

    logger.debug(f"Thin wall check completed in {time.time() - start_time:.3f}s")
    return issues

def check_overhangs_and_support(mesh: trimesh.Trimesh) -> List[DFMIssue]:
    """
    Analyzes face angles to estimate support requirements using Trimesh.

    Args:
        mesh: The Trimesh object of the model.

    Returns:
        List of DFMIssues related to overhangs.
    """
    issues = []
    start_time = time.time()
    warn_angle = CONFIG["warn_overhang_angle_deg"]
    error_angle = CONFIG["error_overhang_angle_deg"]
    # Build direction assumed to be negative Z-axis (0, 0, -1)
    build_vector = np.array([0.0, 0.0, -1.0])

    try:
        # Ensure mesh has faces
        if len(mesh.faces) == 0:
             logger.warning("Cannot check overhangs: Mesh has no faces.")
             return issues

        # Calculate face normals and angles with the build vector
        face_normals = mesh.face_normals
        # Protect against zero vectors if normals somehow are invalid
        face_normals[np.linalg.norm(face_normals, axis=1) == 0] = [0, 0, 1] # Replace bad normals

        face_angles_rad = trimesh.geometry.vector_angle(face_normals, build_vector)
        face_angles_deg = np.degrees(face_angles_rad)

        # Find faces exceeding the warning and error thresholds
        warn_overhang_indices = np.where(face_angles_deg > warn_angle)[0]
        error_overhang_indices = np.where(face_angles_deg > error_angle)[0]

        if len(error_overhang_indices) > 0:
            # Calculate percentage of area requiring error-level support
            overhang_area = mesh.area_faces[error_overhang_indices].sum()
            total_area = mesh.area
            percentage = (overhang_area / total_area) * 100 if total_area > 0 else 0

            issues.append(DFMIssue(
                issue_type=DFMIssueType.SUPPORT_OVERHANG,
                level=DFMLevel.ERROR, # Significant overhangs likely require careful support
                message=f"Significant overhangs detected (>{error_angle}° from vertical, ~{percentage:.1f}% of surface area). These areas will require substantial support.",
                recommendation="Consider reorienting the model to minimize steep overhangs or adding custom supports in CAD if possible. Ensure slicer support settings are robust.",
                visualization_hint={"type": "face_indices", "indices": error_overhang_indices.tolist()},
                details={"overhang_angle_deg": error_angle, "area_percentage": percentage}
            ))
        elif len(warn_overhang_indices) > 0:
            # Only add warning if no error was triggered
            overhang_area = mesh.area_faces[warn_overhang_indices].sum()
            total_area = mesh.area
            percentage = (overhang_area / total_area) * 100 if total_area > 0 else 0

            issues.append(DFMIssue(
                issue_type=DFMIssueType.SUPPORT_OVERHANG,
                level=DFMLevel.WARN,
                message=f"Moderate overhangs detected (>{warn_angle}° from vertical, ~{percentage:.1f}% of surface area). These areas will likely require support.",
                recommendation="Review model orientation. Ensure slicer auto-supports are enabled or add manual supports where needed.",
                visualization_hint={"type": "face_indices", "indices": warn_overhang_indices.tolist()},
                details={"overhang_angle_deg": warn_angle, "area_percentage": percentage}
            ))

    except Exception as e:
        logger.error(f"Error during overhang check: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.SUPPORT_OVERHANG,
            level=DFMLevel.WARN,
            message=f"Could not perform overhang analysis due to an error: {e}",
            recommendation="Manually check model orientation and support requirements."
        ))

    logger.debug(f"Overhang check completed in {time.time() - start_time:.3f}s")
    return issues


def check_warping_risk(mesh: trimesh.Trimesh, mesh_properties: MeshProperties) -> List[DFMIssue]:
    """
    Identifies large, flat areas, especially near the build plate, prone to warping.

    Args:
        mesh: The Trimesh object.
        mesh_properties: Basic properties including bounding box.

    Returns:
        List of DFMIssues related to warping risk.
    """
    issues = []
    start_time = time.time()
    area_threshold_cm2 = CONFIG["large_flat_area_threshold_cm2"]
    z_threshold_mm = 5.0 # Check flat areas within 5mm of the build plate (min_z)

    try:
        # Ensure mesh has faces and properties are valid
        if len(mesh.faces) == 0 or not hasattr(mesh_properties, 'bounding_box'):
            logger.warning("Cannot check warping risk: Mesh has no faces or properties are invalid.")
            return issues

        large_flat_faces = []
        min_z = mesh_properties.bounding_box.min_z

        # Find faces that are nearly horizontal (normal close to +Z or -Z)
        # Use a tolerance, e.g., normal Z component > 0.98 or < -0.98
        z_normal_threshold = 0.98
        # Ensure normals are valid
        face_normals = mesh.face_normals
        face_normals[np.linalg.norm(face_normals, axis=1) == 0] = [0, 0, 1]

        horizontal_indices = np.where(np.abs(face_normals[:, 2]) > z_normal_threshold)[0]

        if len(horizontal_indices) > 0:
            # Check if these faces are near the bottom and part of a large contiguous flat area
            # Group contiguous horizontal faces (this requires graph traversal - complex)
            # Simplification: Check the total area of horizontal faces near the bottom
            bottom_horizontal_indices = []
            face_centroids = mesh.triangles_center[horizontal_indices]
            near_bottom_mask = face_centroids[:, 2] < (min_z + z_threshold_mm)
            bottom_horizontal_indices = horizontal_indices[near_bottom_mask].tolist()

            # Alternative check using vertex Z coordinates
            # bottom_horizontal_indices_alt = []
            # for idx in horizontal_indices:
            #     # Check if any vertex of the face is close to min_z
            #     face_verts = mesh.vertices[mesh.faces[idx]]
            #     if np.any(face_verts[:, 2] < (min_z + z_threshold_mm)):
            #         bottom_horizontal_indices_alt.append(idx)

            if bottom_horizontal_indices:
                 total_bottom_flat_area_mm2 = mesh.area_faces[bottom_horizontal_indices].sum()
                 total_bottom_flat_area_cm2 = total_bottom_flat_area_mm2 / 100.0

                 if total_bottom_flat_area_cm2 > area_threshold_cm2:
                     issues.append(DFMIssue(
                         issue_type=DFMIssueType.WARPING_RISK,
                         level=DFMLevel.WARN,
                         message=f"Large flat area ({total_bottom_flat_area_cm2:.1f} cm²) detected near the build plate (Z < {min_z + z_threshold_mm:.1f}mm). This increases the risk of warping.",
                         recommendation="Consider adding helper structures (brims, rafts), adjusting orientation if possible, or using materials less prone to warping. Ensure good bed adhesion.",
                         # Visualization: Highlight these faces
                         visualization_hint={"type": "face_indices", "indices": bottom_horizontal_indices},
                         details={"flat_area_cm2": total_bottom_flat_area_cm2}
                     ))

    except Exception as e:
        logger.error(f"Error during warping risk check: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.WARPING_RISK,
            level=DFMLevel.WARN,
            message=f"Could not perform warping risk analysis due to an error: {e}",
            recommendation="Manually check for large flat areas, especially near the model base."
        ))

    logger.debug(f"Warping risk check completed in {time.time() - start_time:.3f}s")
    return issues

def check_internal_voids_and_escape(ms: pymeshlab.MeshSet, mesh_properties: MeshProperties, tech: Print3DTechnology) -> List[DFMIssue]:
    """
    Checks for enclosed voids, especially relevant for SLA/SLS needing escape holes.
    Relies on shell count and watertightness checks done previously.

    Args:
        ms: PyMeshLab MeshSet (used to get shell count reliably).
        mesh_properties: Basic properties including volume.
        tech: The printing technology (SLA/SLS are main concern here).

    Returns:
        List of DFMIssues related to internal voids.
    """
    issues = []
    if tech not in [Print3DTechnology.SLA, Print3DTechnology.SLS]:
        return issues # Less critical for FDM

    start_time = time.time()
    shell_count = -1
    volume_threshold = CONFIG["escape_hole_recommendation_threshold_cm3"]

    try:
         # Re-run shell count check for consistency here, using the more reliable method
         # Check if mesh exists
         if not ms.mesh_id_exists(ms.current_mesh_id()):
              raise DFMCheckError("Mesh not available for internal void check.")

         temp_ms = pymeshlab.MeshSet()
         temp_ms.add_mesh(ms.current_mesh(), "temp_mesh_for_voids")
         temp_ms.generate_splitting_by_connected_components()
         shell_count = temp_ms.mesh_number()
         del temp_ms

         # Check if it's a watertight mesh with multiple shells, indicating internal voids
         # Assumes check_mesh_integrity already ran and potentially fixed major holes.
         # We use Trimesh's watertight check here as a reference.
         if mesh_properties.is_watertight and shell_count > 1:
             # Estimate volume of the void(s) - very approximate
             # Calculate volume of bounding box minus volume of the actual mesh
             bbox = mesh_properties.bounding_box
             bbox_volume_cm3 = (bbox.size_x * bbox.size_y * bbox.size_z) / 1000.0
             # This isn't accurate for void volume, but gives a sense of scale
             # A better approach might involve analyzing the volumes of the split shells if possible.
             # For now, use total volume as a proxy for recommending holes if > threshold
             if mesh_properties.volume_cm3 > volume_threshold:
                 issues.append(DFMIssue(
                     issue_type=DFMIssueType.ESCAPE_HOLES,
                     level=DFMLevel.ERROR if tech == Print3DTechnology.SLA else DFMLevel.WARN, # More critical for SLA resin trapping
                     message=f"Model appears to be enclosed and watertight but contains {shell_count} shells, likely indicating internal void(s). This can trap resin (SLA) or powder (SLS).",
                     recommendation=f"Add escape/drain holes (at least 2, minimum ~2-3mm diameter) to allow material removal, especially for {tech.name if isinstance(tech, Print3DTechnology) else tech}. Place them discreetly or near the build plate.",
                     details={"shell_count": shell_count}
                     # Visualization: Would require identifying the inner shell faces, complex.
                 ))
         elif shell_count == -1:
              raise DFMCheckError("Void check failed due to shell count error.")

    except Exception as e:
        logger.error(f"Error during internal void check: {e}", exc_info=True)
        issues.append(DFMIssue(
            issue_type=DFMIssueType.INTERNAL_VOIDS,
            level=DFMLevel.WARN,
            message=f"Could not reliably check for internal voids due to an error: {e}",
            recommendation="Manually inspect the model for enclosed cavities, especially if using SLA or SLS."
        ))

    logger.debug(f"Internal void check completed in {time.time() - start_time:.3f}s")
    return issues


# Add more checks as needed (e.g., minimum feature size, small hole diameter) 