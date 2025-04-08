# api/routers/analysis.py

import logging
import tempfile
import os
import traceback

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from starlette import status

from ..models import AnalysisRequest, AnalysisResponse, ErrorResponse
from ..utils import download_file
from ...services import AnalysisService
from ...core.common_types import AnalysisInput, Print3DTechnology, ProcessType
from ...core.exceptions import ProtonDemandError, AnalysisConfigurationError, MeshProcessingError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
    responses={404: {"description": "Not found"}}
)

# --- Dependency --- #
# In a real app, you might initialize this once and inject it
# For simplicity here, we create it per request or reuse a global instance if needed.
def get_analysis_service():
    # You could load global config here if needed
    # config = load_app_config()
    # return AnalysisService(global_config=config)
    return AnalysisService() # Simple instantiation for now

# --- Helper --- #
def cleanup_temp_file(file_path: str):
    """Safely remove a temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except OSError as e:
        logger.error(f"Error removing temporary file {file_path}: {e}")

# --- Endpoint --- #
@router.post(
    "/",
    response_model=AnalysisResponse,
    summary="Submit a CAD file for DFM analysis and processing",
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"model": ErrorResponse, "description": "Bad Request (e.g., invalid input, download failed)"},
        404: {"model": ErrorResponse, "description": "File not found at URL"},
        413: {"model": ErrorResponse, "description": "File size limit exceeded"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        502: {"model": ErrorResponse, "description": "Bad Gateway (error accessing remote file)"},
        503: {"model": ErrorResponse, "description": "Service Unavailable (network error during download)"}
    }
)
async def run_cad_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Accepts a URL to a CAD file and analysis parameters, downloads the file,
    runs the specified analysis (e.g., 3D print DFM checks, slicing), and
    returns the results.

    - **file_url**: URL to the CAD model (STL, 3MF, OBJ currently supported).
    - **process_type**: Must be "PRINT_3D" currently.
    - **technology**: Specific 3D printing tech (e.g., "FDM", "SLA", "SLS").
    - **material_name**: Material identifier (e.g., "PLA", "ABS-Generic").
    """
    temp_dir = None
    downloaded_file_path = None
    try:
        # 1. Create a temporary directory for the download
        # Use context manager if Python 3.12+, otherwise manual cleanup
        temp_dir = tempfile.mkdtemp(prefix="proton_analysis_")
        logger.debug(f"Created temporary directory: {temp_dir}")

        # 2. Download the file
        # download_file handles errors and raises HTTPException
        downloaded_file_path = await download_file(request.file_url, temp_dir)

        # Add cleanup task for the downloaded file *and* the directory
        background_tasks.add_task(cleanup_temp_file, downloaded_file_path)
        # Ensure directory cleanup happens even if file cleanup fails or file wasn't created
        background_tasks.add_task(lambda d: os.path.exists(d) and os.rmdir(d), temp_dir)

        # 3. Map API input to Core analysis input
        # Perform validation/mapping for technology string to enum
        if request.process_type == ProcessType.PRINT_3D:
            try:
                technology_enum = Print3DTechnology[request.technology.upper()]
            except KeyError:
                 logger.error(f"Invalid Print3DTechnology specified: {request.technology}")
                 raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid 3D printing technology '{request.technology}'. "
                               f"Valid options: {[t.name for t in Print3DTechnology]}"
                    )
        else:
            # Handle other process types if/when added
             logger.error(f"Unsupported process type: {request.process_type}")
             raise HTTPException(
                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                 detail=f"Process type '{request.process_type}' is not currently supported."
             )

        analysis_input = AnalysisInput(
            file_path=downloaded_file_path,
            process_type=request.process_type,
            technology=technology_enum, # Use the validated enum
            material_name=request.material_name,
            # config_overrides=request.config_overrides # Pass if added to request model
        )

        # 4. Run the analysis via the service
        # The service layer handles catching specific ProtonDemandErrors
        core_result = service.run_analysis(analysis_input)

        # 5. Convert core result to API response model
        api_response = AnalysisResponse.from_core(core_result)

        return api_response

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (from download_file or input validation)
        logger.warning(f"HTTPException during analysis request: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except ProtonDemandError as app_exc:
         # Handle known application errors gracefully (e.g., config, mesh processing)
         logger.error(f"Application error during analysis: {app_exc}", exc_info=True)
         status_code = status.HTTP_400_BAD_REQUEST # Default for app errors
         if isinstance(app_exc, AnalysisConfigurationError):
             status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
         elif isinstance(app_exc, MeshProcessingError):
              status_code = status.HTTP_422_UNPROCESSABLE_ENTITY # Often due to bad input file

         raise HTTPException(status_code=status_code, detail=str(app_exc))
    except Exception as e:
        # Catch unexpected errors
        logger.exception("Unexpected error in analysis endpoint") # Log full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {type(e).__name__}"
        )
    # finally:
    #     # Ensure cleanup happens even on unexpected errors if background task fails
    #     # Note: BackgroundTasks are generally reliable, but this is defensive.
    #     # Using BackgroundTasks is preferred as cleanup doesn't block response.
    #     if downloaded_file_path:
    #         cleanup_temp_file(downloaded_file_path)
    #     if temp_dir and os.path.exists(temp_dir):
    #         try:
    #             os.rmdir(temp_dir) # Only removes if empty
    #             logger.debug(f"Removed temporary directory: {temp_dir}")
    #         except OSError as e:
    #              logger.error(f"Could not remove temporary directory {temp_dir}: {e}") 