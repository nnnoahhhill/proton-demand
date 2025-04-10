# processes/print_3d/processor.py

import time
import logging
import os
import tempfile
from typing import List, Dict, Any, Tuple, Optional

import trimesh
import pymeshlab
import numpy as np

# Use absolute imports relative to project root
from processes.base_processor import BaseProcessor
from quote_system.core.common_types import (
    MaterialInfo, MeshProperties,
    ManufacturingProcess, Print3DTechnology, DFMIssue, DFMLevel,
    DFMReport, CostEstimate, QuoteResult, DFMStatus, DFMIssueType
)
from quote_system.core.exceptions import (
    ConfigurationError, SlicerError, DFMCheckError, GeometryProcessingError,
    MaterialNotFoundError # Removed FileNotFoundError
)
from quote_system.core import utils, geometry

# Import specific 3D printing modules using absolute path from project root
from quote_system.processes.print_3d.slicer import run_slicer, SlicerResult, find_slicer_executable
from quote_system.processes.print_3d import dfm_rules # Use absolute import for sibling module

logger = logging.getLogger(__name__)

# Default Settings (same as before)
DEFAULT_LAYER_HEIGHT_MM = { Print3DTechnology.FDM: 0.15, Print3DTechnology.SLA: 0.05, Print3DTechnology.SLS: 0.10, }
DEFAULT_FILL_DENSITY_FDM = 0.20

class Print3DProcessor(BaseProcessor):
    """Processor for analyzing 3D printable models."""

    def __init__(self, markup: float = 1.0):
        # Correct call using absolute path for find_slicer_executable
        from quote_system.processes.print_3d.slicer import find_slicer_executable # Import here if needed only on init
        super().__init__(process_type=ManufacturingProcess.PRINT_3D, markup=markup)
        self._slicer_executable_path: Optional[str] = None
        self._find_and_validate_slicer()

    @property
    def material_file_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), "materials.json")

    def _find_and_validate_slicer(self):
        try:
            # Use function imported from slicer module
            from quote_system.processes.print_3d.slicer import find_slicer_executable
            self._slicer_executable_path = find_slicer_executable()
            if self._slicer_executable_path:
                logger.info(f"Using slicer executable: {self._slicer_executable_path}")
            else:
                logger.warning("Slicer executable (PrusaSlicer) not found. Print time estimates will be unavailable.")
        except Exception as e:
             logger.error(f"Error finding slicer executable: {e}", exc_info=True)
             self._slicer_executable_path = None

    def run_dfm_checks(self,
                       mesh: trimesh.Trimesh,
                       mesh_properties: MeshProperties,
                       material_info: MaterialInfo) -> DFMReport:
        """Runs all configured DFM checks for 3D Printing."""
        dfm_start_time = time.time()
        all_issues: List[DFMIssue] = []

        # Validate technology enum
        try:
            technology = material_info.technology
            if not isinstance(technology, Print3DTechnology):
                 technology = Print3DTechnology(str(material_info.technology))
        except ValueError:
             logger.error(f"Invalid 3D Print tech '{material_info.technology}' for mat '{material_info.id}'.")
             all_issues.append(DFMIssue(issue_type=DFMIssueType.FILE_VALIDATION, level=DFMLevel.CRITICAL, message=f"Invalid technology '{material_info.technology}'."))
             return DFMReport(status=DFMStatus.FAIL, issues=all_issues, analysis_time_sec=time.time() - dfm_start_time)

        logger.info(f"Running DFM checks for: {mesh_properties.vertex_count} vertices, {mesh_properties.face_count} faces. Technology: {technology.name}")

        ms = pymeshlab.MeshSet()
        try:
            # --- FIX: Convert Trimesh to PyMeshLab Mesh ---
            if mesh is not None and len(mesh.vertices) > 0 and len(mesh.faces) > 0:
                pymesh = pymeshlab.Mesh(vertex_matrix=mesh.vertices, face_matrix=mesh.faces)
                ms.add_mesh(pymesh, "input_mesh") # Pass pymeshlab.Mesh
                logger.debug("Successfully added mesh to PyMeshLab MeshSet.")
            else:
                 raise GeometryProcessingError("Input mesh invalid/empty for PyMeshLab.")
            # --- END FIX ---

            # --- Run Individual Checks (Call all checks) ---
            # --- FIX: REMOVED incorrect self._check_mesh_validity_pymeshlab call ---

            all_issues.extend(dfm_rules.check_bounding_box(mesh_properties))
            all_issues.extend(dfm_rules.check_mesh_integrity(ms, mesh, mesh_properties)) # Pass 'mesh' too if needed by rules
            # --- TEMP FIX: Comment out checks for missing pymeshlab filters ---
            # all_issues.extend(dfm_rules.check_thin_walls(ms, technology))
            # all_issues.extend(dfm_rules.check_minimum_features(ms, technology))
            logger.warning("Temporarily skipping thin_walls and minimum_features checks due to missing PyMeshLab filters.")
            # --- END TEMP FIX ---
            all_issues.extend(dfm_rules.check_small_holes(ms, technology))
            all_issues.extend(dfm_rules.check_contact_area_stability(mesh, mesh_properties))
            all_issues.extend(dfm_rules.check_overhangs_and_support(mesh))
            all_issues.extend(dfm_rules.check_warping_risk(mesh, mesh_properties))
            all_issues.extend(dfm_rules.check_internal_voids_and_escape(ms, mesh_properties, technology))

        except DFMCheckError as e: # Catch errors from specific checks
            logger.error(f"A DFM check failed internally: {e}", exc_info=True)
            all_issues.append(DFMIssue( issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.WARN, message=f"DFM analysis check failed: {e}", recommendation="Review manually." ))
        except Exception as e: # Catch unexpected errors during DFM run
            logger.exception("Unexpected error during DFM rule execution:")
            all_issues.append(DFMIssue( issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message=f"Unexpected DFM analysis error: {e}", recommendation="Check logs." ))
        finally:
             if ms is not None: del ms; logger.debug("DFM PyMeshLab MeshSet instance deleted.")

        # Determine overall status based on highest severity issue
        final_status = DFMStatus.PASS
        if any(issue.level == DFMLevel.CRITICAL for issue in all_issues): final_status = DFMStatus.FAIL
        elif any(issue.level == DFMLevel.ERROR for issue in all_issues): final_status = DFMStatus.FAIL
        elif any(issue.level == DFMLevel.WARN for issue in all_issues): final_status = DFMStatus.WARNING

        analysis_time = time.time() - dfm_start_time
        logger.info(f"DFM checks completed in {analysis_time:.3f}s. Status: {final_status.value}, Issues found: {len(all_issues)}")
        return DFMReport(status=final_status, issues=all_issues, analysis_time_sec=analysis_time)


    def calculate_cost_and_time(self,
                                mesh: trimesh.Trimesh,
                                mesh_properties: MeshProperties,
                                material_info: MaterialInfo) -> CostEstimate:
        """Calculates cost and time estimate for 3D printing."""
        cost_start_time = time.time()
        slicer_result: Optional[SlicerResult] = None
        process_time_sec = 0.0
        final_filament_g = 0.0
        final_volume_cm3 = mesh_properties.volume_cm3 # Default to mesh volume

        # Run slicer simulation if path is available
        if self._slicer_executable_path:
            try:
                 logger.info("Running slicer simulation for time/material estimation...")
                 # Need technology enum
                 tech = material_info.technology
                 if not isinstance(tech, Print3DTechnology):
                     tech = Print3DTechnology(str(material_info.technology))

                 # Default settings
                 layer_height = DEFAULT_LAYER_HEIGHT_MM.get(tech, 0.2)
                 fill_density = DEFAULT_FILL_DENSITY_FDM if tech == Print3DTechnology.FDM else 1.0

                 # Create a temporary file for the slicer
                 with tempfile.NamedTemporaryFile(suffix=".stl", delete=False, mode='wb') as tmp_stl_file:
                    mesh.export(file_obj=tmp_stl_file, file_type='stl')
                    tmp_stl_path = tmp_stl_file.name

                 try:
                     slicer_result = run_slicer(
                         stl_file_path=tmp_stl_path,
                         slicer_executable_path=self._slicer_executable_path,
                         layer_height=layer_height,
                         fill_density=fill_density,
                         technology=tech,
                         material_density_g_cm3=material_info.density_g_cm3,
                     )
                     process_time_sec = slicer_result.print_time_seconds
                     # Use slicer results for cost calculation
                     final_filament_g = slicer_result.filament_used_g
                     final_volume_cm3 = slicer_result.filament_used_mm3 / 1000.0
                     logger.info(f"Slicer estimates: Time={utils.format_time(process_time_sec)}, Weight={final_filament_g:.2f}g, Volume={final_volume_cm3:.3f}cm³")
                 finally:
                      # Ensure temp file cleanup
                      if os.path.exists(tmp_stl_path):
                          try: os.unlink(tmp_stl_path)
                          except Exception as e: logger.warning(f"Failed to delete temp slicer file {tmp_stl_path}: {e}")

            except (ConfigurationError, SlicerError, FileNotFoundError) as e:
                 logger.error(f"Slicer execution failed: {e}. Time/Cost accuracy reduced.")
                 # Fallback to heuristic time/cost based on volume? Or fail? Let's fallback.
                 process_time_sec = (mesh_properties.volume_cm3 / 50.0) * 3600.0 # Very rough heuristic
                 final_filament_g = mesh_properties.volume_cm3 * material_info.density_g_cm3
                 final_volume_cm3 = mesh_properties.volume_cm3
                 logger.warning(f"Using heuristic time/cost: Time={utils.format_time(process_time_sec)}, Weight={final_filament_g:.2f}g")
            except Exception as e:
                  logger.exception("Unexpected error during slicer run in cost calculation:")
                  # Fallback as above
                  process_time_sec = (mesh_properties.volume_cm3 / 50.0) * 3600.0
                  final_filament_g = mesh_properties.volume_cm3 * material_info.density_g_cm3
                  final_volume_cm3 = mesh_properties.volume_cm3
                  logger.warning(f"Using heuristic time/cost due to unexpected error: Time={utils.format_time(process_time_sec)}, Weight={final_filament_g:.2f}g")

        else:
            logger.warning("Slicer path not available, using basic volume for cost and heuristic for time.")
            # Fallback heuristic if slicer not found
            process_time_sec = (mesh_properties.volume_cm3 / 50.0) * 3600.0
            final_filament_g = mesh_properties.volume_cm3 * material_info.density_g_cm3
            final_volume_cm3 = mesh_properties.volume_cm3


        # --- Material Cost Calculation (using final weight/volume) ---
        material_cost = 0.0
        if final_filament_g < 0 or final_volume_cm3 < 0:
             logger.warning("Calculated weight/volume is negative, setting material cost to 0.")
             final_filament_g = 0
             final_volume_cm3 = 0
        else:
             if material_info.cost_per_kg is not None and material_info.cost_per_kg > 0:
                 material_cost = (final_filament_g / 1000.0) * material_info.cost_per_kg
             elif material_info.cost_per_liter is not None and material_info.cost_per_liter > 0:
                 material_cost = (final_volume_cm3 / 1000.0) * material_info.cost_per_liter
             else:
                 logger.warning(f"Material '{material_info.id}' has no cost defined. Cost set to 0.")

        base_cost = material_cost # Base cost = Material cost ONLY
        cost_analysis_time = time.time() - cost_start_time
        logger.info(f"Cost & Time calculation finished in {cost_analysis_time:.3f}s. Base Cost: ${base_cost:.2f}, Est Time: {utils.format_time(process_time_sec)}")

        return CostEstimate(
            material_id=material_info.id,
            material_volume_cm3=mesh_properties.volume_cm3, # Original part volume
            support_volume_cm3=None, # Still not explicitly calculated
            total_volume_cm3=final_volume_cm3, # Total used volume (from slicer or base mesh)
            material_weight_g=final_filament_g, # Total used weight (from slicer or base mesh)
            material_cost=round(material_cost, 4),
            process_time_seconds=round(process_time_sec, 3),
            base_cost=round(base_cost, 4),
            cost_analysis_time_sec=cost_analysis_time
        )