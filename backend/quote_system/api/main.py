# api/main.py

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import routers
from .routers import analysis
# Import other routers as needed
# from .routers import health, admin

# Import core exception for potential global handling
from ..core.exceptions import ProtonDemandError

# Configure logging (ensure src/__init__.py sets up basic config)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization --- #

def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""

    app = FastAPI(
        title="ProtonDemand Analysis API",
        description="API for performing Design for Manufacturability (DFM) analysis and processing for various manufacturing methods.",
        version="0.1.0",
        # Add other metadata as needed: docs_url, redoc_url, openapi_url
    )

    # --- Include Routers --- #
    app.include_router(analysis.router)
    # app.include_router(health.router)
    # app.include_router(admin.router)
    logger.info("Included API routers.")

    # --- Exception Handlers --- #
    # Handle Starlette/FastAPI HTTPExceptions (like those raised in endpoints/utils)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTPException caught: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # Handle custom application errors (ProtonDemandError and its subclasses)
    @app.exception_handler(ProtonDemandError)
    async def proton_demand_exception_handler(request: Request, exc: ProtonDemandError):
        # Determine appropriate status code based on error type if needed
        # (Currently handled within the endpoint, but could be centralized here)
        status_code = 400 # Default Bad Request for generic app errors
        logger.error(f"ProtonDemandError caught: {exc}", exc_info=True) # Log with traceback
        return JSONResponse(
            status_code=status_code,
            content={"detail": f"Analysis Error: {exc}"}
        )

    # Generic handler for unexpected errors
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception caught at application level") # Log full traceback
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {type(exc).__name__}"},
        )

    logger.info("Registered exception handlers.")

    # --- Event Handlers (Startup/Shutdown) --- #
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting ProtonDemand Analysis API...")
        # Add any initialization logic here (e.g., connect to DB, load models)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down ProtonDemand Analysis API...")
        # Add cleanup logic here (e.g., close connections)

    return app

# Create the app instance using the factory
app = create_app()

# --- Root Endpoint (Optional) --- #
@app.get("/", tags=["Root"], summary="API Root/Health Check")
async def read_root():
    """Simple endpoint to check if the API is running."""
    return {"message": "ProtonDemand Analysis API is running."}

# --- Run with Uvicorn (for local development) --- #
# This block allows running directly with `python -m api.main`
# However, it's generally recommended to use `uvicorn api.main:app --reload`
# if __name__ == "__main__":
#     import uvicorn
#     # Determine host and port from environment variables or defaults
#     host = os.getenv("API_HOST", "127.0.0.1")
#     port = int(os.getenv("API_PORT", "8000"))
#     log_level = os.getenv("API_LOG_LEVEL", "info").lower()
#     reload = os.getenv("API_RELOAD", "true").lower() == "true"
#
#     print(f"Starting Uvicorn server on {host}:{port} (reload={reload}, log_level={log_level})")
#     uvicorn.run("api.main:app", host=host, port=port, reload=reload, log_level=log_level) 