# processes/print_3d/dfm_rules.py

import time
import logging
from typing import List, Dict, Any, Optional

import numpy as np
import trimesh
import pymeshlab

# Use absolute imports relative to project root
from core.common_types import (
    DFMIssue, DFMLevel, DFMIssueType, MeshProperties, MaterialInfo, Print3DTechnology
)
from core.exceptions import DFMCheckError

logger = logging.getLogger(__name__)

# --- Configuration Thresholds (Same as before) ---
CONFIG = {
    "min_wall_thickness_mm": { "FDM": 0.8, "SLA": 0.4, "SLS": 0.7 },
    "critical_wall_thickness_factor": 0.6,
    "warn_overhang_angle_deg": 45.0,
    "error_overhang_angle_deg": 65.0,
    "min_feature_size_mm": { "FDM": 0.8, "SLA": 0.3, "SLS": 0.6 },
    "min_hole_diameter_mm": { "FDM": 1.0, "SLA": 0.5, "SLS": 0.8 },
    "max_shells_allowed": 1,
    "large_flat_area_threshold_cm2": 50.0,
    "escape_hole_recommendation_threshold_cm3": 5.0,
    "max_bounding_box_mm": {"x": 300, "y": 300, "z": 300},
    "sdf_thin_wall_factor": 1.0,
    "curvature_high_threshold": 0.5, # Heuristic threshold for mean curvature
    "min_contact_area_ratio": 0.005,
    "min_absolute_contact_area_mm2": 10.0
}

# --- Helper Functions ---
def _get_threshold(key: str, tech: Print3DTechnology, default: float) -> float:
    value = CONFIG.get(key)
    if isinstance(value, dict):
        tech_name = tech.name if isinstance(tech, Print3DTechnology) else str(tech)
        return value.get(tech_name, default)
    elif isinstance(value, (int, float)): return value
    return default

# --- DFM Check Functions ---

def check_bounding_box(mesh_properties: MeshProperties) -> List[DFMIssue]:
    # ... (implementation unchanged) ...
    issues = []; max_dims = CONFIG["max_bounding_box_mm"]; bbox = mesh_properties.bounding_box; exceeded = []
    if bbox.size_x > max_dims["x"]: exceeded.append(f"X ({bbox.size_x:.1f}mm > {max_dims['x']}mm)")
    if bbox.size_y > max_dims["y"]: exceeded.append(f"Y ({bbox.size_y:.1f}mm > {max_dims['y']}mm)")
    if bbox.size_z > max_dims["z"]: exceeded.append(f"Z ({bbox.size_z:.1f}mm > {max_dims['z']}mm)")
    if exceeded: issues.append(DFMIssue( issue_type=DFMIssueType.BOUNDING_BOX_LIMIT, level=DFMLevel.CRITICAL, message=f"Model exceeds max build volume: {', '.join(exceeded)}.", recommendation=f"Scale/split model to fit {max_dims['x']}x{max_dims['y']}x{max_dims['z']} mm." ))
    return issues

def check_mesh_integrity(ms: pymeshlab.MeshSet, mesh: trimesh.Trimesh, mesh_properties: MeshProperties) -> List[DFMIssue]:
    """Checks for critical mesh errors like non-manifold, multiple shells, negative volume."""
    issues = []; start_time = time.time()
    if mesh_properties.volume_cm3 < 0: issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message=f"Negative volume ({mesh_properties.volume_cm3:.2f} cm³).", recommendation="Repair normals.")); return issues

    # --- FIX: Use Trimesh for initial manifold check, then PyMeshLab ---
    if not mesh.is_watertight:
        if hasattr(mesh, 'nonmanifold_edges') and len(mesh.nonmanifold_edges) > 0:
            issues.append(DFMIssue(issue_type=DFMIssueType.NON_MANIFOLD, level=DFMLevel.CRITICAL, message=f"Non-manifold edges detected by Trimesh ({len(mesh.nonmanifold_edges)}).", recommendation="Use repair tools."))
        elif hasattr(mesh, 'open_edges') and len(mesh.open_edges) > 0:
            issues.append(DFMIssue(issue_type=DFMIssueType.NON_MANIFOLD, level=DFMLevel.ERROR, message=f"Holes/Open boundary edges detected by Trimesh ({len(mesh.open_edges)}).", recommendation="Use repair tools to close holes."))
        else: # Not watertight but no specific issue found by Trimesh
             # --- FIX: Elevate generic non-watertight from WARN to ERROR --- 
             issues.append(DFMIssue(issue_type=DFMIssueType.NON_MANIFOLD, level=DFMLevel.ERROR, message="Trimesh indicates mesh is not watertight (specific issue not identified).", recommendation="Inspect mesh integrity manually."))
             # --- END FIX ---

    # Proceed with PyMeshLab checks, mainly for topological measures if Trimesh found no critical issues
    if not any(issue.level == DFMLevel.CRITICAL for issue in issues): # Avoid redundant PyMeshLab check if already critical
        non_manifold_edges = 0; non_manifold_vertices = 0; boundary_edges = 0
        try:
            if not ms.current_mesh(): raise DFMCheckError("No current mesh for PyMeshLab topo check.")
            measures = ms.get_topological_measures()
            non_manifold_edges = measures.get('non_manifold_edges', 0); non_manifold_vertices = measures.get('non_manifold_vertices', 0)
            boundary_edges = measures.get('boundary_edges', 0)
            logger.debug(f"PyMeshLab Topo Measures: NM_Edges={non_manifold_edges}, NM_Verts={non_manifold_vertices}, Boundary={boundary_edges}")
            # Only add PyMeshLab issues if they represent a *new* problem or higher severity
            if (non_manifold_edges > 0 or non_manifold_vertices > 0) and not any(i.level == DFMLevel.CRITICAL for i in issues): 
                issues.append(DFMIssue(issue_type=DFMIssueType.NON_MANIFOLD, level=DFMLevel.CRITICAL, message=f"Non-manifold ({non_manifold_edges} edges, {non_manifold_vertices} vertices) found by PyMeshLab.", recommendation="Use repair tools."))
            elif boundary_edges > 0 and not any(i.level >= DFMLevel.ERROR for i in issues): 
                 issues.append(DFMIssue(issue_type=DFMIssueType.NON_MANIFOLD, level=DFMLevel.ERROR, message=f"Holes ({boundary_edges} boundary edges) found by PyMeshLab.", recommendation="Use repair tools to close holes."))
        except Exception as e: logger.error(f"PyMeshLab topo measures error: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.ERROR, message=f"Non-manifold check error (PyMeshLab): {e}", recommendation="Check manually."))

    # Multiple Shells Check - Run PyMeshLab splitting, but IGNORE result if Trimesh said watertight
    # --- FIX: Rework shell check logic to ignore split if trimesh.is_watertight --- 
    logger.debug("Performing PyMeshLab split check for multiple shells...")
    try:
        temp_ms_split = pymeshlab.MeshSet()
        try:
            current_ml_mesh = ms.current_mesh()
            if not current_ml_mesh: raise DFMCheckError("Cannot get current mesh for split check.")
            temp_ms_split.add_mesh(pymeshlab.Mesh(current_ml_mesh.vertex_matrix(), current_ml_mesh.face_matrix()), "mesh_copy_for_split")
            temp_ms_split.meshing_remove_duplicate_vertices()
            temp_ms_split.meshing_remove_duplicate_faces()
            temp_ms_split.generate_splitting_by_connected_components()
            split_shell_count = temp_ms_split.mesh_number()
            logger.info(f"Shell count after splitting verification: {split_shell_count}")
            # ONLY add issue if Trimesh reported NOT watertight AND split found multiple shells
            if not mesh.is_watertight and split_shell_count > CONFIG["max_shells_allowed"]:
                issues.append(DFMIssue(issue_type=DFMIssueType.MULTIPLE_SHELLS, level=DFMLevel.CRITICAL, message=f"Model is not watertight AND contains {split_shell_count} shells (found by splitting). Only {CONFIG['max_shells_allowed']} allowed.", recommendation="Combine parts or ensure connection."))
            elif mesh.is_watertight and split_shell_count > CONFIG["max_shells_allowed"]:
                logger.warning(f"PyMeshLab split found {split_shell_count} shells, but Trimesh reported watertight. Ignoring shell count issue.")
                # Do NOT add an issue in this case
        finally:
            del temp_ms_split # Manual cleanup
    except Exception as e:
        logger.error(f"Shell splitting check failed: {e}", exc_info=True)
        issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.WARN, message=f"Shell count check failed: {e}", recommendation="Manually verify single part."))
    # --- END FIX ---

    logger.debug(f"Mesh integrity checks done in {time.time() - start_time:.3f}s")
    return issues


def check_thin_walls(ms: pymeshlab.MeshSet, tech: Print3DTechnology) -> List[DFMIssue]:
    """Checks for thin walls using PyMeshLab's Shape Diameter Function (SDF)."""
    issues = []; start_time = time.time()
    min_thickness_tech = _get_threshold("min_wall_thickness_mm", tech, 0.8)
    sdf_threshold = min_thickness_tech * CONFIG["sdf_thin_wall_factor"] / 2.0
    critical_sdf_threshold = sdf_threshold * CONFIG["critical_wall_thickness_factor"]
    logger.info(f"Checking thin walls (SDF). Tech={tech.name}, MinThick={min_thickness_tech:.2f}mm, SDF_Thresh={sdf_threshold:.3f}, SDF_Crit={critical_sdf_threshold:.3f}")
    try:
        if not ms.current_mesh(): raise DFMCheckError("No current mesh.")
        # --- FIX: Correct PyMeshLab filter name ---
        filter_name = 'compute_shape_diameter_function'
        if not hasattr(ms, filter_name):
            logger.warning(f"PyMeshLab version {pymeshlab.__version__} lacks '{filter_name}'. Skipping thin wall check.")
            # Optionally add INFO level issue
            issues.append(DFMIssue(issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.INFO, message=f"Thin wall check skipped (filter '{filter_name}' not found in PyMeshLab {pymeshlab.__version__}).", recommendation="Manually verify thicknesses."))
            return issues # Cannot perform check
        # --- END FIX ---
        logger.debug("Computing Shape Diameter Function...")
        ms.compute_shape_diameter_function(sdfmaxanga=90, sdfmaxdist=0, sdfnorm=True) # Corrected name
        logger.debug("SDF computation finished.")
        if not ms.current_mesh().has_vertex_quality(): raise DFMCheckError("SDF failed: No vertex quality.")
        sdf_values = ms.current_mesh().vertex_quality_array()
        if sdf_values is None or len(sdf_values) == 0: raise DFMCheckError("SDF failed: Empty quality array.")
        critical_indices = np.where(sdf_values < critical_sdf_threshold)[0]
        error_warn_indices = np.where((sdf_values >= critical_sdf_threshold) & (sdf_values < sdf_threshold))[0]
        min_critical_sdf = np.min(sdf_values[critical_indices]) if len(critical_indices) > 0 else float('inf')
        min_error_warn_sdf = np.min(sdf_values[error_warn_indices]) if len(error_warn_indices) > 0 else float('inf')
        if len(critical_indices) > 0: issues.append(DFMIssue( issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.CRITICAL, message=f"Critically thin areas (SDF < {critical_sdf_threshold:.3f}, approx thick < ~{critical_sdf_threshold*2:.2f}mm).", recommendation=f"Increase thickness (> {min_thickness_tech:.2f}mm).", visualization_hint={"type": "vertex_indices", "indices": critical_indices.tolist()}, details={"min_sdf_critical": float(min_critical_sdf)} )); logger.warning(f"Critically low SDF: {len(critical_indices)} vertices (min={min_critical_sdf:.3f})")
        if len(error_warn_indices) > 0: issues.append(DFMIssue( issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.ERROR, message=f"Potentially thin walls (SDF < {sdf_threshold:.3f}, approx thick < ~{sdf_threshold*2:.2f}mm).", recommendation=f"Verify/increase thickness to {min_thickness_tech:.2f}mm for {tech.name}.", visualization_hint={"type": "vertex_indices", "indices": error_warn_indices.tolist()}, details={"min_sdf_error": float(min_error_warn_sdf)} )); logger.warning(f"Low SDF: {len(error_warn_indices)} vertices (min={min_error_warn_sdf:.3f})")
        if issues: min_sdf, max_sdf = np.min(sdf_values), np.max(sdf_values); issues[0].visualization_hint = { "type": "vertex_scalar", "name": "ShapeDiameterFunction", "values": sdf_values.tolist(), "cmap_range": [min_sdf, sdf_threshold*1.5]}
    except pymeshlab.PyMeshLabException as pme: logger.error(f"PyMeshLab error (SDF): {pme}", exc_info=False); level = DFMLevel.ERROR if "manifold" in str(pme).lower() else DFMLevel.WARN; issues.append(DFMIssue(issue_type=DFMIssueType.THIN_WALL, level=level, message=f"Thin wall check error (PyMeshLab): {pme}", recommendation="Manually verify thicknesses."))
    except Exception as e: logger.error(f"Error during thin wall check: {e}", exc_info=True); issues.append(DFMIssue( issue_type=DFMIssueType.THIN_WALL, level=DFMLevel.WARN, message=f"Thin wall check error: {e}", recommendation="Manually verify thicknesses." ))
    logger.info(f"Thin wall check done in {time.time() - start_time:.3f}s. Issues: {len(issues)}")
    return issues


def check_minimum_features(ms: pymeshlab.MeshSet, tech: Print3DTechnology) -> List[DFMIssue]:
    """Checks for potentially small features using mean curvature analysis."""
    issues = []; start_time = time.time(); min_feature_size = _get_threshold("min_feature_size_mm", tech, 0.5); curvature_threshold = CONFIG["curvature_high_threshold"]
    logger.info(f"Checking small features (curvature). Tech={tech.name}, MinFeature={min_feature_size:.2f}mm")
    try:
        if not ms.current_mesh(): raise DFMCheckError("No current mesh.")
        # --- FIX: Use simpler mean curvature filter & handle crash ---
        filter_name = 'compute_scalar_mean_curvature_per_vertex'
        if not hasattr(ms, filter_name): raise DFMCheckError(f"PyMeshLab lacks '{filter_name}'.")
        logger.debug("Computing Mean Curvature...")
        ms.compute_scalar_mean_curvature_per_vertex()
        # --- END FIX ---
        if not ms.current_mesh().has_vertex_quality(): raise DFMCheckError("Mean Curvature failed: No vertex quality.")
        mean_curvature_values = np.abs(ms.current_mesh().vertex_quality_array())
        if mean_curvature_values is None or len(mean_curvature_values) == 0: raise DFMCheckError("Mean Curvature failed: Empty quality array.")
        high_curve_indices = np.where(mean_curvature_values > curvature_threshold)[0]
        if len(high_curve_indices) > 0:
             percentage = (len(high_curve_indices) / ms.current_mesh().vertex_number()) * 100
             issues.append(DFMIssue( issue_type=DFMIssueType.SMALL_FEATURE, level=DFMLevel.WARN, message=f"High curvature detected on ~{percentage:.1f}% vertices (> {curvature_threshold:.2f}), potentially small features/sharp corners.", recommendation=f"Inspect high-curvature areas. Ensure features > {min_feature_size:.2f}mm for {tech.name}.", visualization_hint={"type": "vertex_indices", "indices": high_curve_indices.tolist()}, details={"high_curve_threshold": curvature_threshold, "vertex_count": len(high_curve_indices)} ))
    except pymeshlab.PyMeshLabException as pme: logger.error(f"PyMeshLab error during curvature computation: {pme}", exc_info=False); issues.append(DFMIssue(issue_type=DFMIssueType.SMALL_FEATURE, level=DFMLevel.WARN, message=f"Curvature check error (PyMeshLab): {pme}", recommendation=f"Manually inspect features < {min_feature_size:.2f}mm."))
    except Exception as e: logger.error(f"Error during small feature check: {e}", exc_info=True); issues.append(DFMIssue( issue_type=DFMIssueType.SMALL_FEATURE, level=DFMLevel.WARN, message=f"Small feature analysis error: {e}", recommendation=f"Manually inspect features < {min_feature_size:.2f}mm." ))
    logger.debug(f"Small feature check completed in {time.time() - start_time:.3f}s")
    return issues

# Small hole check (unchanged)
def check_small_holes(ms: pymeshlab.MeshSet, tech: Print3DTechnology) -> List[DFMIssue]:
    # ... (implementation unchanged) ...
    issues = []; start_time = time.time(); min_hole_diameter = _get_threshold("min_hole_diameter_mm", tech, 1.0); min_perimeter = np.pi * min_hole_diameter
    logger.info(f"Checking small holes (boundary loops). Tech={tech.name}, MinDiameter={min_hole_diameter:.2f}mm (MinPerim ~{min_perimeter:.2f}mm)")
    try:
        if not ms.current_mesh(): raise DFMCheckError("No current mesh.")
        topo_measures = ms.get_topological_measures(); boundary_edges_count = topo_measures.get('boundary_edges', 0)
        if boundary_edges_count == 0: logger.debug("No boundary edges."); return issues
        current_mesh_from_ms = ms.current_mesh(); mesh_trimesh = trimesh.Trimesh(vertices=current_mesh_from_ms.vertex_matrix(), faces=current_mesh_from_ms.face_matrix())
        if mesh_trimesh.is_watertight: logger.debug("Trimesh watertight, skipping loop check."); return issues
        small_hole_count = 0; problematic_loops_indices = []
        try: loops = mesh_trimesh.outline(face_ids=None)
        except Exception as outline_err: logger.warning(f"Trimesh outline failed: {outline_err}"); loops = None
        if hasattr(loops, 'entities') and loops.entities:
             for entity in loops.entities:
                 if not hasattr(entity, 'points'): continue;
                 if isinstance(entity, trimesh.path.entities.Line): continue
                 loop_vertices = loops.vertices[entity.points]; perimeter = np.sum(np.linalg.norm(np.diff(loop_vertices, axis=0, append=loop_vertices[0:1]), axis=1))
                 if 0 < perimeter < min_perimeter: small_hole_count += 1; problematic_loops_indices.extend(entity.points.tolist()); logger.warning(f"Small hole perimeter {perimeter:.3f}mm")
        if small_hole_count > 0: issues.append(DFMIssue( issue_type=DFMIssueType.SMALL_HOLE, level=DFMLevel.ERROR, message=f"Detected {small_hole_count} hole(s) smaller than printable (min diameter ~{min_hole_diameter:.2f}mm).", recommendation=f"Increase hole diameter >= {min_hole_diameter:.2f}mm or fill.", visualization_hint={"type": "vertex_indices", "indices": list(set(problematic_loops_indices))}, details={"count": small_hole_count, "min_diam_mm": min_hole_diameter} ))
    except ImportError: logger.error("Trimesh unavailable for small hole check."); issues.append(DFMIssue(issue_type=DFMIssueType.SMALL_HOLE, level=DFMLevel.WARN, message="Small hole check failed (missing lib).", recommendation="Manually verify."))
    except Exception as e: logger.error(f"Error during small hole check: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.SMALL_HOLE, level=DFMLevel.WARN, message=f"Small hole analysis error: {e}", recommendation=f"Manually inspect holes < {min_hole_diameter:.2f}mm."))
    logger.debug(f"Small hole check completed in {time.time() - start_time:.3f}s")
    return issues

# Contact area check (unchanged)
def check_contact_area_stability(mesh: trimesh.Trimesh, mesh_properties: MeshProperties) -> List[DFMIssue]:
    # ... (implementation unchanged) ...
    issues = []; start_time = time.time(); min_ratio = CONFIG["min_contact_area_ratio"]; min_abs_area_mm2 = CONFIG["min_absolute_contact_area_mm2"]
    z_tolerance = 0.01; logger.info(f"Checking contact area. MinRatio={min_ratio*100:.2f}%, MinAbsArea={min_abs_area_mm2}mm²")
    try:
        min_z = mesh_properties.bounding_box.min_z; total_area_mm2 = mesh_properties.surface_area_cm2 * 100.0
        bottom_vertex_indices = np.where(mesh.vertices[:, 2] <= min_z + z_tolerance)[0]
        if len(bottom_vertex_indices) < 3: issues.append(DFMIssue(issue_type=DFMIssueType.SUPPORT_OVERHANG, level=DFMLevel.ERROR, message="Point/Line contact with build plate.", recommendation="Reorient or use raft/brim.", details={"bottom_vertex_count": len(bottom_vertex_indices)})); return issues
        bottom_points_2d = mesh.vertices[bottom_vertex_indices][:, :2]; contact_area_mm2 = 0.0
        try:
             from scipy.spatial import ConvexHull
             if len(bottom_points_2d) >= 3: hull = ConvexHull(bottom_points_2d); contact_area_mm2 = hull.volume
        except ImportError: logger.warning("Scipy not installed. Contact area check less accurate."); contact_area_mm2 = 0.0 # Handle fallback if needed
        except Exception as hull_err: logger.error(f"Error calculating convex hull: {hull_err}"); contact_area_mm2 = 0.0
        contact_ratio = (contact_area_mm2 / total_area_mm2) if total_area_mm2 > 0 else 0
        if contact_area_mm2 < min_abs_area_mm2 or contact_ratio < min_ratio: issues.append(DFMIssue(issue_type=DFMIssueType.SUPPORT_OVERHANG, level=DFMLevel.WARN, message=f"Small contact area (~{contact_area_mm2:.2f} mm², {contact_ratio*100:.2f}%). Adhesion/stability risk.", recommendation="Use brim/raft. Consider reorientation.", details={"contact_area_mm2": contact_area_mm2, "contact_ratio": contact_ratio}))
    except Exception as e: logger.error(f"Error during contact area check: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.WARN, message=f"Contact area analysis error: {e}", recommendation="Manually check orientation."))
    logger.debug(f"Contact area check completed in {time.time() - start_time:.3f}s")
    return issues


def check_overhangs_and_support(mesh: trimesh.Trimesh) -> List[DFMIssue]:
    """Analyzes face angles to estimate support requirements."""
    issues = []; start_time = time.time(); warn_angle = CONFIG["warn_overhang_angle_deg"]; error_angle = CONFIG["error_overhang_angle_deg"]
    build_vector = np.array([0.0, 0.0, -1.0]) # Downward vector
    try:
        if len(mesh.faces) == 0: return issues
        # --- FIX: Copy face normals ---
        face_normals = mesh.face_normals.copy()
        # --- END FIX ---
        norm_lengths = np.linalg.norm(face_normals, axis=1); zero_norm_mask = norm_lengths < 1e-8
        if np.any(zero_norm_mask): face_normals[zero_norm_mask] = [0, 0, 1]; logger.warning(f"Replaced {np.sum(zero_norm_mask)} zero normals.")

        # --- FIX: Manual Angle Calculation ---
        # 1. Filter for downward-pointing faces
        downward_mask = face_normals[:, 2] < -1e-6
        if not np.any(downward_mask): logger.debug("No downward faces for overhang."); return issues

        downward_normals = face_normals[downward_mask]
        downward_face_indices = np.where(downward_mask)[0]

        # 2. Calculate angle with the *downward* vector build_vector ([0, 0, -1])
        norms = np.linalg.norm(downward_normals, axis=1)
        valid_norms_mask = norms > 1e-6
        if not np.any(valid_norms_mask): logger.warning("All downward faces had zero normals."); return issues

        normalized_downward_normals = downward_normals[valid_norms_mask] / norms[valid_norms_mask, np.newaxis]
        valid_downward_face_indices = downward_face_indices[valid_norms_mask]

        # Dot product gives cosine of angle between vectors
        dot_products = np.dot(normalized_downward_normals, build_vector)
        dot_products = np.clip(dot_products, -1.0, 1.0) # Clip for arccos stability
        angles_rad = np.arccos(dot_products) # Angle is 0 for horizontal-down, 90 for vertical
        angles_deg = np.degrees(angles_rad)

        # 3. Check thresholds (angle > threshold means needs support)
        error_mask = angles_deg > error_angle
        warn_mask = (angles_deg > warn_angle) & (angles_deg <= error_angle)
        # --- END FIX ---

        error_indices_original = valid_downward_face_indices[error_mask].tolist()
        warn_indices_original = valid_downward_face_indices[warn_mask].tolist()

        # Calculate area percentage... (rest of logic unchanged)
        if not hasattr(mesh, 'area_faces') or len(mesh.area_faces) != len(mesh.faces): logger.warning("Missing/mismatched area_faces.");
        else:
            total_area = mesh.area; total_area = 1.0 if total_area <= 0 else total_area
            if len(error_indices_original) > 0:
                overhang_area = mesh.area_faces[error_indices_original].sum(); percentage = (overhang_area / total_area) * 100
                issues.append(DFMIssue( issue_type=DFMIssueType.SUPPORT_OVERHANG, level=DFMLevel.ERROR, message=f"Significant overhangs (>{error_angle}°, ~{percentage:.1f}% area).", recommendation="Reorient or add custom supports.", visualization_hint={"type": "face_indices", "indices": error_indices_original}, details={"angle": error_angle, "area%": percentage} ))
            elif len(warn_indices_original) > 0:
                 overhang_area = mesh.area_faces[warn_indices_original].sum(); percentage = (overhang_area / total_area) * 100
                 issues.append(DFMIssue( issue_type=DFMIssueType.SUPPORT_OVERHANG, level=DFMLevel.WARN, message=f"Moderate overhangs (>{warn_angle}°, ~{percentage:.1f}% area).", recommendation="Enable auto-supports.", visualization_hint={"type": "face_indices", "indices": warn_indices_original}, details={"angle": warn_angle, "area%": percentage} ))
    except Exception as e: logger.error(f"Error during overhang check: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.SUPPORT_OVERHANG, level=DFMLevel.WARN, message=f"Overhang analysis error: {e}", recommendation="Manually check supports."))
    logger.debug(f"Overhang check completed in {time.time() - start_time:.3f}s")
    return issues


def check_warping_risk(mesh: trimesh.Trimesh, mesh_properties: MeshProperties) -> List[DFMIssue]:
    """Identifies large, flat areas near the build plate."""
    issues = []; start_time = time.time(); area_threshold_cm2 = CONFIG["large_flat_area_threshold_cm2"]; z_threshold_mm = 5.0
    try:
        if len(mesh.faces) == 0 or not hasattr(mesh_properties, 'bounding_box'): return issues
        min_z = mesh_properties.bounding_box.min_z
        # --- FIX: Copy face normals ---
        face_normals = mesh.face_normals.copy()
        # --- END FIX ---
        norm_lengths = np.linalg.norm(face_normals, axis=1); zero_norm_mask = norm_lengths < 1e-8
        if np.any(zero_norm_mask): face_normals[zero_norm_mask] = [0, 0, 0] # Set zero vector to avoid angle errors

        z_normal_threshold = 0.98; horizontal_indices = np.where(np.abs(face_normals[:, 2]) > z_normal_threshold)[0]
        if len(horizontal_indices) > 0:
            bottom_horizontal_indices = []; face_centroids = mesh.triangles_center[horizontal_indices]
            near_bottom_mask = face_centroids[:, 2] < (min_z + z_threshold_mm)
            bottom_horizontal_indices = horizontal_indices[near_bottom_mask].tolist()
            if bottom_horizontal_indices:
                 if not hasattr(mesh, 'area_faces') or len(mesh.area_faces) != len(mesh.faces): logger.warning("Missing area_faces in warping check.")
                 else:
                     total_bottom_flat_area_mm2 = mesh.area_faces[bottom_horizontal_indices].sum(); total_bottom_flat_area_cm2 = total_bottom_flat_area_mm2 / 100.0
                     if total_bottom_flat_area_cm2 > area_threshold_cm2: issues.append(DFMIssue( issue_type=DFMIssueType.WARPING_RISK, level=DFMLevel.WARN, message=f"Large flat area ({total_bottom_flat_area_cm2:.1f} cm²) near base. Warping risk.", recommendation="Use brims/rafts, manage temps.", visualization_hint={"type": "face_indices", "indices": bottom_horizontal_indices}, details={"flat_area_cm2": total_bottom_flat_area_cm2} ))
    except Exception as e: logger.error(f"Error during warping risk check: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.WARPING_RISK, level=DFMLevel.WARN, message=f"Warping risk analysis error: {e}", recommendation="Manually check flat areas."))
    logger.debug(f"Warping risk check completed in {time.time() - start_time:.3f}s")
    return issues


def check_internal_voids_and_escape(ms: pymeshlab.MeshSet, mesh_properties: MeshProperties, tech: Print3DTechnology) -> List[DFMIssue]:
    """Checks for enclosed voids, relevant for SLA/SLS."""
    issues = []; start_time = time.time()
    if tech not in [Print3DTechnology.SLA, Print3DTechnology.SLS]: return issues
    volume_threshold = CONFIG["escape_hole_recommendation_threshold_cm3"]; shell_count = -1
    try:
         if not ms.current_mesh(): raise DFMCheckError("No mesh for void check.")
         # --- FIX: Correct context manager handling ---
         temp_ms = pymeshlab.MeshSet()
         try:
             current_ml_mesh = ms.current_mesh(); temp_ms.add_mesh(pymeshlab.Mesh(current_ml_mesh.vertex_matrix(), current_ml_mesh.face_matrix()), "temp_for_voids"); temp_ms.generate_splitting_by_connected_components(); shell_count = temp_ms.mesh_number()
         finally:
             del temp_ms # Ensure cleanup
         # --- END FIX ---

         # --- FIX: Check shell count even if not watertight ---
         if shell_count > 1: # If splitting results in more than one shell
             if mesh_properties.volume_cm3 > volume_threshold: issues.append(DFMIssue( issue_type=DFMIssueType.ESCAPE_HOLES, level=DFMLevel.ERROR if tech == Print3DTechnology.SLA else DFMLevel.WARN, message=f"Model has {shell_count} shells (internal voids?). May trap material.", recommendation=f"Add escape/drain holes (~2-3mm) for {tech.name}.", details={"shell_count": shell_count} ))
         # --- END FIX ---
         elif shell_count == -1: raise DFMCheckError("Void check failed due to shell count error.")
    except Exception as e: logger.error(f"Error during internal void check: {e}", exc_info=True); issues.append(DFMIssue(issue_type=DFMIssueType.INTERNAL_VOIDS, level=DFMLevel.WARN, message=f"Could not reliably check voids: {e}", recommendation="Manually inspect."))
    logger.debug(f"Internal void check completed in {time.time() - start_time:.3f}s")
    return issues