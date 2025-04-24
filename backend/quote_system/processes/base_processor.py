# processes/base_processor.py

import os
import time
import logging
import json
import abc
import trimesh  # For base validation
from typing import List, Dict, Any, Optional, Tuple, cast
import math

# Change to relative imports
from ..core.common_types import (
    QuoteResult,
    DFMReport, 
    DFMIssue,
    DFMStatus,
    DFMLevel,
    DFMIssueType,
    ManufacturingProcess,
    MaterialInfo,
    MeshProperties,
    CostEstimate
)
from ..core.exceptions import (
    MaterialNotFoundError, 
    FileFormatError, 
    GeometryProcessingError, 
    ConfigurationError, 
    SlicerError, # If base class needs to potentially catch it
    ManufacturingQuoteError # General custom error
)
from ..core import geometry, utils # Import necessary core modules
from ..config import settings # Import settings

logger = logging.getLogger(__name__)

class BaseProcessor(abc.ABC):
    """
    Abstract Base Class for all manufacturing process analysis handlers.
    Defines the common interface for DFM checks, costing, and quoting.
    """

    def __init__(self, process_type: ManufacturingProcess, markup: float = 1.0):
        """
        Initializes the BaseProcessor.

        Args:
            process_type: The specific manufacturing process this processor handles.
            markup: The markup factor to apply to the base cost for the customer price.
                    A markup of 1.0 means 0% markup, 1.5 means 50% markup.
        """
        self.process_type = process_type
        self.materials: Dict[str, MaterialInfo] = {}
        self.markup = max(1.0, markup) # Ensure markup is at least 1.0 (0%)
        self._load_material_data() # Load materials on initialization

    @property
    @abc.abstractmethod
    def material_file_path(self) -> str:
        """Abstract property that must return the path to the process-specific material JSON file."""
        pass

    def _load_material_data(self):
        """Loads material data from the JSON file specified by material_file_path."""
        if not self.material_file_path or not os.path.exists(self.material_file_path):
            logger.error(f"Material file not found for {self.process_type}: {self.material_file_path}")
            raise ConfigurationError(f"Material definition file missing for {self.process_type}.")

        try:
            with open(self.material_file_path, 'r') as f:
                materials_data = json.load(f)

            self.materials = {}
            for mat_data in materials_data:
                # Validate that the material is for the correct process type
                if mat_data.get("process") != self.process_type.value:
                     logger.warning(f"Skipping material '{mat_data.get('id', 'N/A')}' "
                                    f"defined in {os.path.basename(self.material_file_path)} "
                                    f"as its process ('{mat_data.get('process')}') "
                                    f"does not match processor type ('{self.process_type.value}').")
                     continue

                try:
                     # Use Pydantic model for validation and type coercion
                     material = MaterialInfo(**mat_data)
                     self.materials[material.id] = material
                except Exception as pydantic_e: # Catch Pydantic validation errors
                     logger.warning(f"Skipping invalid material definition in "
                                    f"{os.path.basename(self.material_file_path)} "
                                    f"for ID '{mat_data.get('id', 'N/A')}': {pydantic_e}")
                     continue

            if not self.materials:
                logger.warning(f"No valid materials loaded for {self.process_type} from {self.material_file_path}.")
            else:
                logger.info(f"Successfully loaded {len(self.materials)} materials for {self.process_type}.")

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from material file {self.material_file_path}: {e}", exc_info=True)
            raise ConfigurationError(f"Invalid JSON in material file: {self.material_file_path}") from e
        except Exception as e:
            logger.error(f"Unexpected error loading material file {self.material_file_path}: {e}", exc_info=True)
            raise ConfigurationError(f"Could not load materials for {self.process_type}") from e

    def get_material_info(self, material_id: str) -> MaterialInfo:
        """
        Retrieves the MaterialInfo object for a given material ID.

        Args:
            material_id: The unique identifier of the material.

        Returns:
            The corresponding MaterialInfo object.

        Raises:
            MaterialNotFoundError: If the material_id is not found for this process.
        """
        material = self.materials.get(material_id)
        if not material:
            logger.error(f"Material ID '{material_id}' not found for process {self.process_type}.")
            # Provide available materials in the error message for better context
            available_ids = list(self.materials.keys())
            raise MaterialNotFoundError(
                f"Material '{material_id}' is not available for {self.process_type}. "
                f"Available materials: {available_ids}"
            )
        return material

    def list_available_materials(self) -> List[Dict[str, Any]]:
         """Returns a list of available materials for this process."""
         # Use model_dump instead of dict
         return [mat.model_dump() for mat in self.materials.values()]


    @abc.abstractmethod
    def run_dfm_checks(self, mesh: trimesh.Trimesh, mesh_properties: MeshProperties, material_info: MaterialInfo) -> DFMReport:
        """
        Performs Design for Manufacturing checks specific to the process.

        Args:
            mesh: The Trimesh object of the model.
            mesh_properties: Basic properties derived from the mesh.
            material_info: Details of the selected material.

        Returns:
            A DFMReport object containing the status and list of issues.
        """
        pass

    @abc.abstractmethod
    def calculate_cost_and_time(self, mesh: trimesh.Trimesh, mesh_properties: MeshProperties, material_info: MaterialInfo) -> CostEstimate:
        """
        Calculates the estimated material cost and process time.
        Base cost MUST only include material cost as per user requirement.

        Args:
            mesh: The Trimesh object of the model (may be needed for advanced cost calcs).
            mesh_properties: Basic properties derived from the mesh (volume, area etc.).
            material_info: Details of the selected material (cost, density).

        Returns:
            A CostEstimate object containing the breakdown.
        """
        pass

    def generate_quote(self, file_path: str, material_id: str) -> QuoteResult:
        """
        Orchestrates the full quote generation process: load, DFM, cost, time.

        Args:
            file_path: Path to the input model file (STL or STEP).
            material_id: The ID of the material to use for quoting.

        Returns:
            A QuoteResult object containing the full quote details or DFM failures.
        """
        total_start_time = time.time()
        logger.info(f"Generating quote for: {os.path.basename(file_path)}, Material: {material_id}, Process: {self.process_type.value}")

        # Initialize quote_result BEFORE the main try block
        quote_result = QuoteResult(
            file_name=os.path.basename(file_path),
            process=self.process_type,
            # Remaining fields will be populated or remain None
            material_info=None, 
            dfm_report=None, 
            cost_estimate=None,
            customer_price=None,
            estimated_process_time_str=None,
            processing_time_sec=-1, # Will be updated in finally
            error_message=None
        )

        mesh = None
        mesh_properties = None
        dfm_report = None
        cost_estimate = None
        customer_price = None
        error_message = None
        material_info = None
        estimated_process_time_str = "N/A"

        try:
            # Start by loading the mesh
            logger.info(f"Loading mesh from {file_path}")
            mesh = geometry.load_mesh(file_path) # Raises FileNotFoundError, FileFormatError, GeometryProcessingError, StepConversionError
            
            # Get the mesh properties using our geometric analysis functions
            mesh_properties = geometry.get_mesh_properties(mesh)
            logger.info(f"Mesh properties: {mesh_properties}")

            # Load material configuration
            material_info = self.get_material_info(material_id)
            logger.info(f"Using material: {material_info.name}")

            # Perform basic Design For Manufacturing checks
            dfm_start_time = time.time()
            dfm_report = self.run_dfm_checks(mesh, mesh_properties, material_info)
            dfm_report.analysis_time_sec = time.time() - dfm_start_time
            quote_result.dfm_report = dfm_report # Store DFM report regardless of status
            logger.info(f"DFM analysis complete. Status: {dfm_report.status}, Time: {dfm_report.analysis_time_sec:.2f}s")
            # Log DFM issues if any
            if dfm_report.status != DFMStatus.PASS:
                for issue in dfm_report.issues:
                    logger.warning(f"  - DFM Issue [{issue.level} - {issue.issue_type}]: {issue.message} {issue.details or ''}")

            # Always attempt Cost & Time Estimation, regardless of DFM status
            logger.info(f"Proceeding with cost/time estimation (DFM Status was: {dfm_report.status})...")
            cost_start_time = time.time()
            # This might raise exceptions (SlicerError, ConfigError etc.) if issues occur here
            cost_estimate = self.calculate_cost_and_time(mesh, mesh_properties, material_info)
            cost_estimate.cost_analysis_time_sec = time.time() - cost_start_time
            quote_result.cost_estimate = cost_estimate
            
            # Calculate marked-up price (Base Cost * Markup)
            markup_price = cost_estimate.base_cost * self.markup

            # Calculate time-based cost
            time_cost = (cost_estimate.process_time_seconds / 3600) * settings.print_time_cost_per_hour

            # Final customer price = Marked-up Price + Time Cost
            final_customer_price = markup_price + time_cost
            
            # Round up to nearest cent
            customer_price = math.ceil(final_customer_price * 100) / 100  
            quote_result.customer_price = customer_price
            
            # Format estimated time
            estimated_process_time_str = utils.format_time(cost_estimate.process_time_seconds)
            quote_result.estimated_process_time_str = estimated_process_time_str
            
            logger.info(f"Cost/Time estimation complete. Base Cost: {cost_estimate.base_cost:.2f}, Markup Price: {markup_price:.2f}, Time Cost: {time_cost:.2f}, Final Price: {customer_price:.2f}, Time: {estimated_process_time_str}, Analysis Time: {cost_estimate.cost_analysis_time_sec:.2f}s")
            error_message = None # Clear any potential previous error message if costing succeeded
            quote_result.error_message = None # Explicitly clear error on success path
            # Set success flag to True since price was calculated
            quote_result.success = True

        # --- Exception Handling Block Starts Here --- 
        except (MaterialNotFoundError, FileNotFoundError, FileFormatError, GeometryProcessingError, ConfigurationError, SlicerError, ManufacturingQuoteError) as e:
            logger.error(f"Quote generation failed for {os.path.basename(file_path)} due to: {e}", exc_info=True) # Log full trace for operational errors
            # Populate error message in the result
            error_message = f"{type(e).__name__}: {str(e)}"
            quote_result.error_message = error_message
            # Ensure DFM report is populated if error occurred after DFM
            if quote_result.dfm_report is None: 
                 quote_result.dfm_report = DFMReport(status=DFMStatus.FAIL, issues=[DFMIssue(issue_type=DFMIssueType.FILE_VALIDATION if isinstance(e, (FileNotFoundError, FileFormatError)) else DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message=str(e))], analysis_time_sec=0)
            elif quote_result.dfm_report.status != DFMStatus.FAIL:
                # Add the exception as a critical DFM issue if it happened after DFM
                quote_result.dfm_report.status = DFMStatus.FAIL
                quote_result.dfm_report.issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message=f"Processing Error: {str(e)}"))
                
        except Exception as e:
            # Catch any other unexpected errors
            logger.exception(f"Unexpected error during quote generation for {os.path.basename(file_path)}:")
            error_message = f"Unexpected Internal Error: {str(e)}"
            quote_result.error_message = error_message
            # Ensure DFM report reflects failure
            if quote_result.dfm_report is None:
                 quote_result.dfm_report = DFMReport(status=DFMStatus.FAIL, issues=[DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message="Unexpected internal error during processing.")], analysis_time_sec=0)
            else:
                quote_result.dfm_report.status = DFMStatus.FAIL
                if not any(iss.message.startswith("Unexpected Internal Error") for iss in quote_result.dfm_report.issues):
                    quote_result.dfm_report.issues.append(DFMIssue(issue_type=DFMIssueType.GEOMETRY_ERROR, level=DFMLevel.CRITICAL, message=f"Unexpected Internal Error: {str(e)}"))

        total_processing_time = time.time() - total_start_time
        logger.info(f"Quote generation finished in {total_processing_time:.3f} seconds. Status: {dfm_report.status if dfm_report else 'Error'}")

        # Ensure dfm_report is always populated, even in case of early error
        if dfm_report is None:
             # This should only happen if an error occurred before DFM could even start
             dfm_report = DFMReport(
                  status=DFMStatus.FAIL,
                  issues=[DFMIssue(
                      issue_type=DFMIssueType.GEOMETRY_ERROR,
                      level=DFMLevel.CRITICAL,
                      message=error_message or "Quote generation failed before DFM analysis.",
                      recommendation="Check file and system logs."
                  )],
                  analysis_time_sec=0
             )

        # Ensure material_info is populated if possible, even on failure
        if material_info is None:
             # Create a dummy material info if lookup failed but we know the ID
             try:
                  material_info = MaterialInfo(
                       id=material_id, name=f"{material_id} (Info Missing)",
                       process=self.process_type, density_g_cm3=0, # Dummy values
                       cost_per_kg=None, cost_per_liter=None # Indicate missing cost info
                  )
             except Exception: # If even creating dummy fails (e.g., bad process type)
                  material_info = MaterialInfo(id="unknown", name="Unknown", process=self.process_type, density_g_cm3=0)

        quote_result.material_info = material_info
        quote_result.dfm_report = dfm_report
        quote_result.cost_estimate = cost_estimate
        quote_result.customer_price = customer_price
        quote_result.estimated_process_time_str = estimated_process_time_str if cost_estimate else None
        quote_result.processing_time_sec = total_processing_time
        quote_result.error_message = error_message

        # Return the QuoteResult instance that was initialized earlier
        return quote_result 