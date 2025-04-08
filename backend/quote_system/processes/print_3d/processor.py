# processes/print_3d/processor.py

import time
import logging
import os
import tempfile
from typing import List, Dict, Any, Tuple, Optional

import trimesh
import pymeshlab
import numpy as np

from ..base_processor import BaseProcessor, AnalysisResult
from ...core.common_types import (
    AnalysisInput, AnalysisConfig, MaterialInfo, MeshProperties,
    ProcessType, Print3DTechnology, DFMIssue, DFMLevel
)
from ...core.exceptions import MeshProcessingError, AnalysisConfigurationError, DFMCheckError
from ...core.geometry import load_mesh, calculate_mesh_properties, repair_mesh
from ...core.utils import format_time_delta
from .slicer import run_slicer, SlicerResult, find_slicer_executable
from .dfm_rules import (
    check_bounding_box,
    check_mesh_integrity,
    check_thin_walls,
    check_overhangs_and_support,
    check_warping_risk,
    check_internal_voids_and_escape,
    # Import other check functions as they are added
)

logger = logging.getLogger(__name__)

# --- Configuration ---
DEFAULT_SLICER_SETTINGS = {
    "layer_height": 0.2,
    "fill_density": 20, # Percent
    "support_material_angle": 45, # Degrees
    "print_speed": 60, # mm/s
    "material_bed_temperature": 60, # Celsius
    "material_print_temperature": 210 # Celsius
}

class Print3DProcessor(BaseProcessor):
    """Processor for analyzing 3D printable models (STL, 3MF, OBJ)."""

    SUPPORTED_FILE_TYPES = [".stl", ".3mf", ".obj"]
    PROCESS_TYPE = ProcessType.PRINT_3D

    def __init__(self, config: Optional[AnalysisConfig] = None):
        super().__init__(config)
        # Specific initialization for 3D printing, e.g., find slicer
        self.slicer_path = find_slicer_executable()
        if not self.slicer_path:
            logger.warning("Slicer executable not found. Print time/material estimates will be unavailable.")
        # Load default materials for 3D printing
        self._load_materials("processes/print_3d/materials.json") # Path relative to src root

    def _validate_config(self, analysis_input: AnalysisInput):
        """Validate technology and material compatibility."""
        super()._validate_config(analysis_input)

        if not isinstance(analysis_input.technology, Print3DTechnology):
            raise AnalysisConfigurationError(
                f"Invalid technology specified ({analysis_input.technology}). "
                f"Expected a Print3DTechnology enum (e.g., FDM, SLA, SLS)."
            )

        if analysis_input.material_name not in self.materials:
            raise AnalysisConfigurationError(
                f"Material '{analysis_input.material_name}' is not supported or defined for 3D Printing."
                f" Available materials: {list(self.materials.keys())}"
            )

        mat_info = self.materials[analysis_input.material_name]
        if analysis_input.technology not in mat_info.compatible_processes:
             raise AnalysisConfigurationError(
                f"Material '{analysis_input.material_name}' is not compatible with technology "
                f"'{analysis_input.technology.name}'. Compatible technologies: {mat_info.compatible_processes}"
            )

        logger.info(f"Configuration validated for {analysis_input.technology.name} with {analysis_input.material_name}.")

    def _run_dfm_checks(self,
                        mesh: trimesh.Trimesh,
                        ms: pymeshlab.MeshSet,
                        mesh_properties: MeshProperties,
                        tech: Print3DTechnology,
                        material: MaterialInfo) -> List[DFMIssue]:
        """Runs all configured DFM checks for the given mesh and technology."""
        start_time = time.time()
        issues: List[DFMIssue] = []

        logger.info(f"Starting DFM checks for technology: {tech.name}")

        # Define the checks to run
        # Could potentially make this configurable
        check_functions = [
            check_bounding_box, # Check first as it's fundamental
            check_mesh_integrity,
            check_thin_walls,
            check_overhangs_and_support,
            check_warping_risk,
            check_internal_voids_and_escape,
        ]

        # Prepare arguments for checks
        # Some checks need ms, some mesh, some properties, some tech/material
        # Use a dictionary or similar to pass args selectively if needed, or pass all

        for check_func in check_functions:
            check_start_time = time.time()
            try:
                logger.debug(f"Running DFM check: {check_func.__name__}")
                # Determine args needed by inspecting signature or using try-except (less clean)
                # Simplified: Pass common args, let functions ignore what they don't need (requires careful function design)
                # Or use explicit arg passing based on function name/metadata (more robust)
                if check_func is check_bounding_box:
                     new_issues = check_func(mesh_properties)
                elif check_func is check_mesh_integrity:
                    # Check if ms is usable, otherwise handle error gracefully
                    current_mesh_id = ms.current_mesh_id()
                    if current_mesh_id == -1 or not ms.mesh_id_exists(current_mesh_id):
                        logger.error(f"MeshSet has no current mesh for {check_func.__name__}, skipping.")
                        # Optionally add a generic DFM issue indicating check couldn't run
                        new_issues = [DFMIssue(
                            issue_type=DFMIssueType.GEOMETRY_ERROR,
                            level=DFMLevel.WARN,
                            message=f"DFM Check '{check_func.__name__}' skipped: Invalid MeshSet state.",
                            recommendation="Ensure mesh loaded correctly."
                        )]
                    else:
                        new_issues = check_func(ms, mesh, mesh_properties)
                elif check_func is check_thin_walls:
                     new_issues = check_func(ms, tech)
                elif check_func is check_overhangs_and_support:
                     new_issues = check_func(mesh)
                elif check_func is check_warping_risk:
                    new_issues = check_func(mesh, mesh_properties)
                elif check_func is check_internal_voids_and_escape:
                    new_issues = check_func(ms, mesh_properties, tech)
                else:
                     logger.warning(f"Unhandled DFM check function: {check_func.__name__}")
                     new_issues = []

                if new_issues:
                    issues.extend(new_issues)
                    for issue in new_issues:
                         logger.debug(f"  - Issue found ({issue.level.name}): {issue.message}")
                logger.debug(f"Check {check_func.__name__} finished in {time.time() - check_start_time:.3f}s")

            except DFMCheckError as dfm_err:
                logger.error(f"DFM Check '{check_func.__name__}' failed: {dfm_err}", exc_info=True)
                issues.append(DFMIssue(
                    issue_type=DFMIssueType.ANALYSIS_ERROR,
                    level=DFMLevel.WARN,
                    message=f"DFM Check '{check_func.__name__}' failed: {dfm_err}",
                    recommendation="Review logs for details. Mesh may need repair or check parameters adjusted."
                ))
            except Exception as e:
                logger.error(f"Unexpected error during DFM check '{check_func.__name__}': {e}", exc_info=True)
                issues.append(DFMIssue(
                    issue_type=DFMIssueType.ANALYSIS_ERROR,
                    level=DFMLevel.ERROR,
                    message=f"Unexpected error in '{check_func.__name__}': {e}",
                    recommendation="Report this error. Check logs for details."
                ))

        total_time = time.time() - start_time
        logger.info(f"DFM checks completed in {format_time_delta(total_time)}. Found {len(issues)} issues.")
        return issues

    def _get_slicer_settings(self, material: MaterialInfo, tech: Print3DTechnology) -> Dict[str, Any]:
        """Prepare slicer settings based on material and technology defaults."""
        settings = DEFAULT_SLICER_SETTINGS.copy()
        # Override defaults with material-specific properties if available
        settings["material_print_temperature"] = material.properties.get("print_temperature_celsius", settings["material_print_temperature"])
        settings["material_bed_temperature"] = material.properties.get("bed_temperature_celsius", settings["material_bed_temperature"])
        # Could add tech-specific overrides here too
        # Example:
        # if tech == Print3DTechnology.SLA:
        #     settings['layer_height'] = 0.05 # Finer default for SLA
        # elif tech == Print3DTechnology.FDM:
        #      pass # Use general default

        logger.debug(f"Generated slicer settings: {settings}")
        return settings

    def analyze(self, analysis_input: AnalysisInput) -> AnalysisResult:
        """Performs DFM analysis and slicing simulation for a 3D model."""
        start_time_total = time.time()
        logger.info(f"Starting 3D Print analysis for: {analysis_input.file_path}")
        self._validate_config(analysis_input)

        results: Dict[str, Any] = {}
        dfm_issues: List[DFMIssue] = []
        slicer_result: Optional[SlicerResult] = None
        mesh_properties: Optional[MeshProperties] = None
        mesh: Optional[trimesh.Trimesh] = None
        ms: Optional[pymeshlab.MeshSet] = None
        material_info = self.materials[analysis_input.material_name]

        try:
            # 1. Load Mesh (using Trimesh primarily, fallback PyMeshLab if needed)
            start_time = time.time()
            logger.info("Loading mesh...")
            mesh = load_mesh(analysis_input.file_path, self.SUPPORTED_FILE_TYPES)
            logger.info(f"Mesh loaded in {format_time_delta(time.time() - start_time)}.")

            # 2. Initial Mesh Properties Calculation
            start_time = time.time()
            logger.info("Calculating initial mesh properties...")
            # Ensure mesh is not None before proceeding
            if mesh is None:
                raise MeshProcessingError("Mesh loading failed, cannot proceed.")
            mesh_properties = calculate_mesh_properties(mesh)
            results["initial_properties"] = mesh_properties.to_dict()
            logger.info(f"Initial properties calculated in {format_time_delta(time.time() - start_time)}: Volume={mesh_properties.volume_cm3:.2f} cm³, BB={mesh_properties.bounding_box.to_tuple()}")

            # 3. Mesh Repair (using PyMeshLab)
            start_time = time.time()
            logger.info("Repairing mesh using PyMeshLab...")
            # Need MeshSet for repair and some DFM checks
            ms = pymeshlab.MeshSet()
            try:
                # Add mesh to MeshSet
                ms.add_mesh(mesh, mesh.metadata.get('file_name', os.path.basename(analysis_input.file_path)))
                repaired_ms, repair_log = repair_mesh(ms)
                results["repair_log"] = repair_log
                logger.info(f"Mesh repair attempted in {format_time_delta(time.time() - start_time)}. Log: {repair_log}")
                ms = repaired_ms # Use the repaired meshset from now on
                # Optionally, update trimesh object from repaired pymeshlab mesh if needed
                # mesh = convert_pymeshlab_to_trimesh(ms.current_mesh()) # Requires conversion helper
                # If mesh is updated, recalculate properties
                # mesh_properties = calculate_mesh_properties(mesh)
                # results["repaired_properties"] = mesh_properties.to_dict()
            except Exception as repair_err:
                logger.error(f"Error during PyMeshLab mesh repair: {repair_err}", exc_info=True)
                # Decide how to handle repair failure: proceed with original mesh? Add DFM issue?
                dfm_issues.append(DFMIssue(
                    issue_type=DFMIssueType.GEOMETRY_ERROR,
                    level=DFMLevel.WARN,
                    message=f"Mesh repair process failed: {repair_err}. Proceeding with original/partially repaired mesh.",
                    recommendation="Inspect model for errors manually."
                ))
                # If repair failed critically, ms might be unusable. Ensure ms is valid or reset it.
                if ms.number_meshes() == 0:
                    logger.warning("MeshSet is empty after repair failure. Some DFM checks may be skipped.")
                    # Potentially try adding the original mesh again if ms is empty
                    try:
                         ms.add_mesh(mesh, mesh.metadata.get('file_name', os.path.basename(analysis_input.file_path)))
                         logger.info("Re-added original mesh to MeshSet after repair failure.")
                    except Exception as add_err:
                         logger.error(f"Failed to re-add original mesh to MeshSet: {add_err}")
                         ms = None # Mark MeshSet as unusable

            # Ensure ms is available for DFM checks that need it
            if ms is None or ms.number_meshes() == 0:
                logger.error("MeshSet unavailable, some DFM checks will be skipped.")
                # Append a DFM issue indicating this state
                dfm_issues.append(DFMIssue(
                     issue_type=DFMIssueType.ANALYSIS_ERROR,
                     level=DFMLevel.WARN,
                     message="Mesh processing failed to produce a valid state for all DFM checks.",
                     recommendation="Review mesh loading and repair logs."
                ))
                # Fallback: create an empty MeshSet to avoid None checks later, though checks needing it will fail/skip
                if ms is None:
                    ms = pymeshlab.MeshSet()

            # Ensure mesh_properties is not None before DFM checks
            if mesh_properties is None:
                 raise MeshProcessingError("Initial mesh properties calculation failed, cannot proceed with DFM checks.")

            # 4. Run DFM Checks
            dfm_issues.extend(self._run_dfm_checks(
                mesh, ms, mesh_properties, analysis_input.technology, material_info
            ))
            results["dfm_issues"] = [issue.to_dict() for issue in dfm_issues]

            # 5. Slicing Simulation (if slicer available and no CRITICAL DFM issues)
            critical_issues = any(issue.level == DFMLevel.CRITICAL for issue in dfm_issues)
            if not self.slicer_path:
                logger.warning("Skipping slicing simulation: Slicer path not configured.")
                results["slicing_skipped_reason"] = "Slicer path not configured"
            elif critical_issues:
                 logger.warning(f"Skipping slicing simulation due to {sum(1 for i in dfm_issues if i.level == DFMLevel.CRITICAL)} CRITICAL DFM issue(s).")
                 results["slicing_skipped_reason"] = "Critical DFM issues found"
            else:
                start_time = time.time()
                logger.info("Running slicing simulation...")
                slicer_settings = self._get_slicer_settings(material_info, analysis_input.technology)

                # Need to save the mesh (potentially the repaired one) to a temporary file
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Choose file format supported by slicer (STL is common)
                    tmp_mesh_path = os.path.join(tmpdir, "temp_mesh.stl")
                    try:
                        # Export from PyMeshLab if it holds the repaired mesh
                        if ms.number_meshes() > 0:
                            ms.save_current_mesh(tmp_mesh_path)
                            logger.debug(f"Saved current mesh from MeshSet to {tmp_mesh_path}")
                        elif mesh:
                            # Fallback to exporting original trimesh object
                            mesh.export(tmp_mesh_path)
                            logger.debug(f"Saved original Trimesh object to {tmp_mesh_path}")
                        else:
                            raise MeshProcessingError("No valid mesh available to save for slicing.")

                        slicer_result = run_slicer(
                            slicer_path=self.slicer_path,
                            mesh_file=tmp_mesh_path,
                            output_dir=tmpdir, # Slicer writes gcode here
                            config_overrides=slicer_settings
                        )
                        results["slicing"] = slicer_result.to_dict()
                        logger.info(f"Slicing simulation completed in {format_time_delta(time.time() - start_time)}.")
                        logger.info(f" -> Estimated Print Time: {slicer_result.estimated_print_time_sec:.0f}s")
                        logger.info(f" -> Estimated Material Usage: {slicer_result.material_usage_mm3:.1f} mm³ / {slicer_result.material_usage_grams:.1f} g")

                    except FileNotFoundError:
                        logger.error(f"Slicer executable not found at: {self.slicer_path}")
                        results["slicing_error"] = f"Slicer not found at {self.slicer_path}"
                    except (MeshProcessingError, ValueError, RuntimeError, TimeoutError) as slice_err:
                         logger.error(f"Slicing simulation failed: {slice_err}", exc_info=True)
                         results["slicing_error"] = str(slice_err)
                    except Exception as e:
                         logger.exception(f"Unexpected error during slicing: {e}") # Use logger.exception for stack trace
                         results["slicing_error"] = f"Unexpected error: {e}"

        except (MeshProcessingError, AnalysisConfigurationError) as e:
            logger.error(f"Analysis aborted due to configuration or mesh processing error: {e}", exc_info=True)
            # Add a critical DFM issue to indicate failure
            dfm_issues.append(DFMIssue(
                 issue_type=DFMIssueType.ANALYSIS_ERROR,
                 level=DFMLevel.CRITICAL,
                 message=f"Analysis failed: {e}",
                 recommendation="Check input file, configuration, and logs."
            ))
            results["error"] = str(e)
            results["dfm_issues"] = [issue.to_dict() for issue in dfm_issues] # Ensure issues are in results
        except Exception as e:
            logger.exception("An unexpected error occurred during analysis.") # Captures stack trace
            dfm_issues.append(DFMIssue(
                 issue_type=DFMIssueType.ANALYSIS_ERROR,
                 level=DFMLevel.CRITICAL,
                 message=f"Unexpected analysis error: {e}",
                 recommendation="Report this error. Check logs for details."
            ))
            results["error"] = f"Unexpected analysis error: {e}"
            results["dfm_issues"] = [issue.to_dict() for issue in dfm_issues]
        finally:
             # Clean up PyMeshLab instance if created
             if ms is not None:
                  del ms # Helps release memory potentially held by MeshLab internals
                  logger.debug("PyMeshLab MeshSet instance deleted.")

        total_analysis_time = time.time() - start_time_total
        logger.info(f"Total analysis finished in {format_time_delta(total_analysis_time)}.")

        return AnalysisResult(
            success=results.get("error") is None,
            message="Analysis complete" if results.get("error") is None else results.get("error", "Analysis failed"),
            process_type=self.PROCESS_TYPE,
            results=results,
            dfm_issues=dfm_issues,
            input_parameters=analysis_input.to_dict(),
            execution_time_ms=int(total_analysis_time * 1000)
        ) 