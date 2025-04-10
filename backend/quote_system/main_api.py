# main_api.py

import os
import time
import logging
import tempfile
from typing import Dict, List, Any, Optional

from fastapi import (
    FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks, Query
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Project specific imports
from config import settings, setup_logging
from core.common_types import (
    QuoteResult,
    ManufacturingProcess,
    MaterialInfo,
    DFMReport,
    DFMIssue
)
from core.exceptions import (
    MaterialNotFoundError, FileFormatError, GeometryProcessingError, ConfigurationError
)
# Import Processors (using dynamic import based on process type)
from quote_system.processes.print_3d.processor import Print3DProcessor
from quote_system.processes.cnc.processor import CncProcessor
# from processes.sheet_metal.processor import SheetMetalProcessor # When available
from core import processor_factory

# Initial setup
setup_logging()
logger = logging.getLogger(__name__)

# --- Initialize Processors ---
# Instantiate processors once, potentially based on settings
# Use markup from loaded settings
PROCESSORS: Dict[ManufacturingProcess, Any] = {}
try:
    PROCESSORS[ManufacturingProcess.PRINT_3D] = Print3DProcessor(markup=settings.markup_factor)
    logger.info("3D Print Processor Initialized.")
except Exception as e:
    logger.error(f"Failed to initialize 3D Print Processor: {e}", exc_info=True)

try:
    PROCESSORS[ManufacturingProcess.CNC] = CncProcessor(markup=settings.markup_factor)
    logger.info("CNC Processor Initialized.")
except Exception as e:
    logger.error(f"Failed to initialize CNC Processor: {e}", exc_info=True)

# try:
#     PROCESSORS[ManufacturingProcess.SHEET_METAL] = SheetMetalProcessor(markup=settings.markup_factor)
#     logger.info("Sheet Metal Processor Initialized.")
# except Exception as e:
#     logger.error(f"Failed to initialize Sheet Metal Processor: {e}", exc_info=True)


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Manufacturing Instant Quote API",
    description="Provides DFM analysis and instant quotes for 3D Printing and CNC Machining.",
    version="1.0.0",
    # Add lifespan context manager if needed for startup/shutdown events
)

# --- CORS Middleware ---
# Allow all origins for now, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Functions ---
def get_processor(process: ManufacturingProcess):
    """Gets the initialized processor for the requested manufacturing process."""
    processor = PROCESSORS.get(process)
    if not processor:
        logger.error(f"No processor available or initialized for process: {process.value}")
        raise HTTPException(
            status_code=501, # Not Implemented
            detail=f"Processing for '{process.value}' is not available or not configured correctly."
        )
    return processor

async def save_upload_file_tmp(upload_file: UploadFile) -> str:
    """Saves UploadFile to a temporary file and returns the path."""
    try:
        # Create a temporary file with the correct suffix
        suffix = os.path.splitext(upload_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="api_upload_") as tmp_file:
            content = await upload_file.read()
            tmp_file.write(content)
            return tmp_file.name
    except Exception as e:
        logger.error(f"Failed to save uploaded file '{upload_file.filename}' to temp location: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process uploaded file.")

def cleanup_temp_file(file_path: str):
    """Removes a temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary file '{file_path}': {e}")


# --- API Endpoints ---

@app.get("/", tags=["General"])
async def get_root():
    """Returns basic API information."""
    available_processes = [p.value for p in PROCESSORS.keys()]
    return {
        "service": "Manufacturing Instant Quote API",
        "version": "1.0.0",
        "status": "operational",
        "available_processes": available_processes
    }

@app.get("/health", tags=["General"])
async def get_health():
    """Health check endpoint."""
    # Can add more checks here (e.g., slicer availability)
    slicer_ok = PROCESSORS.get(ManufacturingProcess.PRINT_3D, None) is not None # Basic check
    return {"status": "ok", "timestamp": time.time(), "checks": {"slicer_init": slicer_ok}}

@app.get("/materials/{process_value}", response_model=List[MaterialInfo], tags=["Materials"])
async def list_materials(process_value: str):
    """
    Lists available materials for a specified manufacturing process.
    Use process values like '3D Printing', 'CNC Machining'.
    """
    try:
        # Convert string value from path to Enum member
        process = ManufacturingProcess(process_value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid process name '{process_value}'. Valid names are: {[p.value for p in ManufacturingProcess]}"
        )

    try:
        processor = get_processor(process) # Raises 501 if not available
        materials = processor.list_available_materials()
        # Pydantic automatically validates the response against List[MaterialInfo]
        return materials
    except Exception as e:
        # Catch potential errors during material listing (e.g., file not found in processor init)
        logger.error(f"Error listing materials for {process.value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not retrieve materials for {process.value}.")


@app.post("/quote", response_model=QuoteResult, tags=["Quoting"])
async def create_quote(
    background_tasks: BackgroundTasks,
    model_file: UploadFile = File(..., description="3D model file (.stl, .step, .stp)"),
    process: ManufacturingProcess = Form(..., description=f"Manufacturing process ({', '.join([p.value for p in ManufacturingProcess])})"),
    material_id: str = Form(..., description="Material ID (use /materials/{process} endpoint to find available IDs)")
):
    """
    Analyzes a 3D model, performs DFM checks, and returns an instant quote.
    """
    tmp_file_path = None
    try:
        # 1. Save uploaded file
        # Run file saving in background? No, need the file content immediately.
        tmp_file_path = await save_upload_file_tmp(model_file)
        # Ensure temporary file is cleaned up after request finishes
        background_tasks.add_task(cleanup_temp_file, tmp_file_path)

        # 2. Get the appropriate processor
        processor = get_processor(process) # Raises 501 HTTPException if unavailable

        # 3. Generate the quote using the processor
        logger.info(f"API: Calling generate_quote for {model_file.filename}, Process: {process}, Material: {material_id}")
        quote: QuoteResult = processor.generate_quote(
            file_path=tmp_file_path,
            material_id=material_id
            # Markup is already set in the processor instance
        )
        logger.info(f"API: Quote generated with ID {quote.quote_id}, Status: {quote.dfm_report.status}")

        # 4. Return the result
        # FastAPI automatically converts the Pydantic model to JSON
        return quote

    # --- Specific Error Handling ---
    except MaterialNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) # 404 Not Found for material
    except FileNotFoundError as e: # Should be caught by save_upload_file_tmp or processor
        raise HTTPException(status_code=400, detail=f"Input file error: {e}")
    except (FileFormatError, GeometryProcessingError) as e:
         raise HTTPException(status_code=400, detail=f"Invalid model file: {e}") # 400 Bad Request
    except ConfigurationError as e:
        # E.g., Slicer not found when needed by Print3DProcessor
        logger.error(f"Configuration error during quote: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Service configuration error: {e}") # 503 Service Unavailable
    except SlicerError as e:
        logger.error(f"Slicer error during quote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error during print time estimation: {e}")
    except ManufacturingQuoteError as e:
        # Catch other custom errors from the application
        logger.error(f"Quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {e}")
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error during /quote endpoint processing:")
        raise HTTPException(status_code=500, detail=f"An unexpected internal server error occurred: {e}")
    finally:
        # Redundant cleanup using BackgroundTasks is preferred, but can add here as failsafe
        # if tmp_file_path:
        #     cleanup_temp_file(tmp_file_path) # Ensure cleanup even if background task fails?
        pass

# --- Optional: Add endpoint for LLM enhanced explanations ---
# @app.post("/quote/{quote_id}/enhanced-explanation", tags=["Quoting"])
# async def get_enhanced_explanation(quote_id: str):
#    # Requires storing quote results (e.g., in memory cache or DB)
#    # Fetch quote result
#    # If DFM issues exist and LLM API key is configured:
#    #   Call LLM service with issue details
#    #   Return enhanced explanation
#    raise HTTPException(status_code=501, detail="Not Implemented Yet")

# --- Run Instruction (for direct execution, though usually run with uvicorn command) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server via __main__ (use 'uvicorn main_api:app --reload' for development)")
    uvicorn.run(app, host="0.0.0.0", port=8000) 