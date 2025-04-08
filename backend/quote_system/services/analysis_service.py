# services/analysis_service.py

import logging
from typing import Dict, Any, Optional

from ..core.common_types import AnalysisInput, AnalysisResult, ProcessType, AnalysisConfig
from ..processes import get_processor
from ..core.exceptions import ProtonDemandError

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service layer responsible for handling analysis requests."""

    def __init__(self, global_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AnalysisService.

        Args:
            global_config: Optional dictionary containing global configuration
                           settings for the analysis processes (e.g., API keys,
                           default paths, global thresholds).
        """
        self.global_config = global_config or {}
        logger.info("AnalysisService initialized.")
        # Potentially pre-initialize processors or load resources here
        # if it offers a performance benefit and makes sense.

    def run_analysis(self, analysis_input: AnalysisInput) -> AnalysisResult:
        """
        Runs the appropriate analysis based on the input process type.

        Args:
            analysis_input: The input data for the analysis.

        Returns:
            An AnalysisResult object containing the outcome.

        Raises:
            NotImplementedError: If the process type is not supported.
            ProtonDemandError: For known analysis errors.
            Exception: For unexpected errors during analysis.
        """
        logger.info(f"Received analysis request for process: {analysis_input.process_type.name}, "
                    f"file: {analysis_input.file_path}")

        try:
            # Create an AnalysisConfig object potentially merging global and input configs
            # For now, just passing global config, processor can decide how to use it
            analysis_config = AnalysisConfig(config_data=self.global_config)

            # Get the appropriate processor using the factory function
            processor = get_processor(analysis_input.process_type, config=analysis_config)

            # Run the analysis
            result = processor.analyze(analysis_input)

            logger.info(f"Analysis completed for {analysis_input.file_path}. Success: {result.success}")
            if not result.success:
                 logger.warning(f"Analysis for {analysis_input.file_path} failed. Message: {result.message}")
            if result.dfm_issues:
                 logger.info(f"Found {len(result.dfm_issues)} DFM issues for {analysis_input.file_path}.")

            return result

        except NotImplementedError as e:
            logger.error(f"Analysis failed: {e}")
            # Re-raise or return a specific error result
            # return AnalysisResult(success=False, message=str(e), ...) # Example
            raise e # Re-raising for now
        except ProtonDemandError as e:
            # Handle known application-specific errors gracefully
            logger.error(f"Analysis failed due to ProtonDemandError: {e}", exc_info=True)
            return AnalysisResult(
                success=False,
                message=f"Analysis Error: {e}",
                process_type=analysis_input.process_type,
                results={"error_details": str(e)},
                dfm_issues=[], # Or potentially add a critical issue
                input_parameters=analysis_input.to_dict(),
                execution_time_ms=0 # Or measure time until error
            )
        except Exception as e:
            # Handle unexpected errors
            logger.exception("An unexpected error occurred during analysis execution.") # Includes stack trace
            # Return a generic failure result
            return AnalysisResult(
                success=False,
                message=f"An unexpected error occurred: {e}",
                process_type=analysis_input.process_type,
                results={"error_details": f"Unexpected error: {e}"},
                dfm_issues=[], # Or add a critical issue
                input_parameters=analysis_input.to_dict(),
                execution_time_ms=0
            ) 