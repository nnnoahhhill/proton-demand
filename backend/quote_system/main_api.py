# main_api.py

import os
import re  # For regex pattern matching
import time
import logging
import tempfile
import json # For Slack payload
import requests # For Slack notification
import asyncio # For background file cleanup/upload task
import shutil # For file operations
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path # Use pathlib for easier path manipulation
from enum import Enum
import sys
import uuid
from logging.handlers import RotatingFileHandler

import stripe # Import Stripe
from pydantic import BaseModel # For request bodies

from fastapi import (
    FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks, Query,
    Request, Header # Added for webhook
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Project specific imports
# Use relative import for config as it's in the same directory
from .config import settings
from .core.common_types import (
    QuoteResult,
    ManufacturingProcess,
    MaterialInfo,
    DFMReport,
    DFMIssue,
)
from .core.exceptions import (
    MaterialNotFoundError, FileFormatError, GeometryProcessingError, ConfigurationError,
    SlicerError, ManufacturingQuoteError # Added missing specific errors
)
# Import Processors (using dynamic import based on process type)
# Use relative imports because we are inside the quote_system directory
from .processes.print_3d.processor import Print3DProcessor
from .processes.cnc.processor import CncProcessor
# from .processes.sheet_metal.processor import SheetMetalProcessor # When available

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient # Use AsyncWebClient
from .utils import get_base_quote_id_py # Import the helper function

# Initial setup
# Set up enhanced logging configuration
# Create a logs directory at project root level if it doesn't exist
project_root = Path(__file__).resolve().parent.parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure root logger for both console and file logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create formatters
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Use a format string that doesn't require session_id for the main logger
file_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - [%(name)s] - %(message)s')

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Default file handler for general system logs
general_log_file = logs_dir / "api_system.log"
file_handler = RotatingFileHandler(
    general_log_file, maxBytes=10*1024*1024, backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Session log files will be created dynamically for each checkout session or order

def get_session_logger(session_id):
    """
    Creates or gets a logger for a specific checkout/payment session.
    Uses a unique file for each session ID.
    """
    # Use a clean session ID that's safe for filenames
    safe_session_id = str(session_id).replace('/', '_').replace('\\', '_')
    
    # Create a timestamp-based log filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{safe_session_id}_{timestamp}.log"
    log_path = logs_dir / log_filename
    
    # Create a new logger for this session
    session_logger = logging.getLogger(f"{__name__}.session.{safe_session_id}")
    session_logger.setLevel(logging.DEBUG)
    
    # Create a special formatter for session logs that includes the session_id
    session_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - [%(name)s] - [Session: %(session_id)s] - %(message)s')
    
    # Add a file handler specifically for this session
    handler = logging.FileHandler(log_path)
    handler.setFormatter(session_formatter)
    session_logger.addHandler(handler)
    
    # Create a filter to add session_id to the log record
    class SessionFilter(logging.Filter):
        def filter(self, record):
            record.session_id = safe_session_id
            return True
    
    session_logger.addFilter(SessionFilter())
    
    # Log the creation of this session logger (but don't use session_id in this message format)
    logger.info(f"Created session-specific log file for {session_id}: {log_path}")
    
    # Now log to the session logger
    session_logger.info(f"Session logger initialized")
    
    return session_logger

# --- Temporary In-Memory Storage for File Paths --- 
# WARNING: This is NOT suitable for production. 
# File paths are lost on server restart.
# A proper solution involves persistent storage (DB or cloud storage).
temp_file_storage: Dict[str, str] = {}

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
    description="Provides DFM analysis and instant quotes for 3D Printing and CNC Machining. Includes Payment Intent flow.",
    version="1.2.0", # Incremented version
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

# --- Stripe Initialization ---
# Load Stripe key from settings
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key
    logger.info(f"Stripe API key loaded: {settings.stripe_secret_key[:5]}...{settings.stripe_secret_key[-4:]}")
    
    # Let's verify that the webhook secret is also available
    if settings.stripe_webhook_secret:
        logger.info(f"Stripe webhook secret loaded: {settings.stripe_webhook_secret[:5]}...{settings.stripe_webhook_secret[-4:]}")
    else:
        logger.warning("Stripe webhook secret is missing. Webhook validation will not work.")
else:
    logger.warning("Stripe API key not found. Payment processing will be disabled.")

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

def cleanup_temp_file_and_storage(quote_id: Optional[str], file_path: Optional[str]):
    """Removes a temporary file and its entry from temp_file_storage."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
        # Remove from temp storage regardless of file existence
        if quote_id in temp_file_storage:
            del temp_file_storage[quote_id]
            logger.debug(f"Removed quote_id {quote_id} from temporary file storage.")
    except Exception as e:
        logger.warning(f"Error during cleanup for quote {quote_id} ('{file_path}'): {e}")

async def send_slack_notification(payload_blocks: List[Dict[str, Any]], fallback_text: str, file_path: Optional[str] = None, file_name: Optional[str] = None, quote_id: Optional[str] = None):
    """Sends a notification with optional file upload to Slack using slack_sdk."""
    slack_token = getattr(settings, 'slack_bot_token', os.getenv('SLACK_BOT_TOKEN'))
    channel_id = getattr(settings, 'slack_upload_channel_id', os.getenv('SLACK_UPLOAD_CHANNEL_ID'))

    if not slack_token or not channel_id:
        logger.warning("Slack Bot Token or Channel ID missing. Skipping notification.")
        # If file path was provided, ensure cleanup happens even if notification fails
        if file_path and quote_id:
             cleanup_temp_file_and_storage(quote_id, file_path)
        return

    client = AsyncWebClient(token=slack_token)

    try:
        if file_path and file_name and os.path.exists(file_path):
            logger.info(f"Attempting Slack upload for {file_name} (Quote: {quote_id}) with initial message.")
            response = await client.files_upload_v2(
                channel=channel_id,
                file=file_path,
                filename=file_name,
                initial_comment=fallback_text, # Use fallback text as simple comment
                request_file_info=False # Don't need full file info response
            )
            # Note: files_upload_v2 doesn't directly support Block Kit in initial_comment easily.
            # A follow-up chat_postMessage is needed for rich formatting.
            if response.get("ok"):
                logger.info(f"Successfully uploaded {file_name} for quote {quote_id}.")
                # Send the rich message as a separate message referencing the file?
                # Or maybe just rely on the initial_comment? For now, let's send the rich message AFTER upload.
                try:
                    await client.chat_postMessage(
                        channel=channel_id,
                        blocks=payload_blocks,
                        text=fallback_text # Fallback for notifications
                    )
                    logger.info("Sent detailed Block Kit message after file upload.")
                except SlackApiError as post_err:
                     logger.error(f"Failed to send Block Kit message after file upload for {quote_id}: {post_err.response['error']}", exc_info=True)

            else:
                error_msg = response.get('error', 'Unknown error')
                logger.error(f"Slack API error uploading file for quote {quote_id}: {error_msg}")
                # Try sending the text message anyway if upload failed
                await client.chat_postMessage(
                    channel=channel_id,
                    blocks=payload_blocks,
                    text=fallback_text # Fallback for notifications
                )
        elif file_path:
             logger.error(f"File path {file_path} provided for quote {quote_id} but file not found. Sending text message only.")
             # Send text message only
             await client.chat_postMessage(
                 channel=channel_id,
                 blocks=payload_blocks,
                 text=fallback_text # Fallback for notifications
             )
        else:
            # Send standard text/block message without file
            logger.info(f"Sending standard Slack message for quote {quote_id or 'N/A'}.")
            await client.chat_postMessage(
                channel=channel_id,
                blocks=payload_blocks,
                text=fallback_text # Fallback for notifications
            )
        logger.info(f"Slack notification processed for quote {quote_id or 'N/A'}.")

    except SlackApiError as e:
        logger.error(f"Slack API error for quote {quote_id or 'N/A'}: {e.response['error']}", exc_info=True)
    except FileNotFoundError: # Should be caught by os.path.exists, but just in case
         logger.error(f"File {file_path} disappeared before Slack operation for quote {quote_id}.", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during Slack notification/upload for quote {quote_id or 'N/A'}: {e}", exc_info=True)
    finally:
         # Cleanup should happen if file_path was provided, regardless of success/failure
         if file_path and quote_id:
             # Use background task to ensure cleanup doesn't block
             # Need BackgroundTasks instance here... refactor might be needed
             # For simplicity now, call directly - potential delay if cleanup is slow
             cleanup_temp_file_and_storage(quote_id, file_path)

# --- Add find_order_folder_py helper ---

def find_order_folder_py(base_quote_id: str, payment_intent_id: Optional[str] = None) -> Optional[str]:
    """Finds the order-specific subfolder in storage/models based on the base quote ID and payment intent ID."""
    try:
        # Construct the expected base path
        # Ensure this matches the structure used in lib/storage.ts
        project_root = Path(__file__).resolve().parent.parent.parent # Go up 3 levels from backend/quote_system/main_api.py
        models_dir = project_root / "storage" / "models"
        
        if not models_dir.is_dir():
            logger.error(f"Models directory not found at: {models_dir}")
            return None

        logger.info(f"Searching for order folder with base ID '{base_quote_id}' and payment intent ID '{payment_intent_id or 'N/A'}' in {models_dir}")
        
        # First, try to find by payment_intent_id if provided
        if payment_intent_id:
            for item in models_dir.iterdir():
                # Check if it's a directory and starts with the payment intent ID + hyphen
                if item.is_dir() and item.name.startswith(f"{payment_intent_id}-"):
                    logger.info(f"Found matching order folder by payment intent ID: {item}")
                    return str(item) # Return the full path as a string
        
        # If no payment intent folder found, try finding by quote ID
        for item in models_dir.iterdir():
            # Check if it's a directory and starts with the base quote ID + hyphen
            if item.is_dir() and item.name.startswith(f"{base_quote_id}-"):
                logger.info(f"Found matching order folder by quote ID: {item}")
                return str(item) # Return the full path as a string
        
        # No existing folder found, create a new one
        logger.warning(f"No existing order folder found. Creating new folder.")
        
        # Create timestamp in PST timezone for folder name
        from datetime import datetime, timezone, timedelta
        utc_now = datetime.now(timezone.utc)
        pst_offset = timedelta(hours=-7) # Assuming PDT for now
        pst_time = utc_now.astimezone(timezone(pst_offset))
        timestamp = pst_time.strftime('%m-%d-%Y--%H-%M-%S')
        
        # Use payment_intent_id for folder name if available, otherwise use quote ID
        folder_name = f"{payment_intent_id}-{timestamp}" if payment_intent_id else f"{base_quote_id}-{timestamp}"
        new_folder = models_dir / folder_name
        
        # Create the folder
        new_folder.mkdir(exist_ok=True)
        logger.info(f"Created new order folder: {new_folder}")
        
        return str(new_folder)

    except Exception as e:
        logger.error(f"Error finding order folder for {base_quote_id} and {payment_intent_id or 'N/A'}: {e}", exc_info=True)
        return None

# --- Pydantic Models for API ---

# Model for Stripe Checkout Session Request (Matches frontend lib/api.ts)
class CheckoutSessionRequest(BaseModel):
    item_name: str
    price: float # Expect price in major currency unit (e.g., dollars)
    currency: Optional[str] = 'usd'
    quantity: Optional[int] = 1
    quote_id: Optional[str] = None
    # Add file_name to be passed from frontend
    file_name: Optional[str] = None 

# Model for Stripe Checkout Session Response (Matches frontend lib/api.ts)
class CheckoutSessionResponse(BaseModel):
    sessionId: str
    url: Optional[str] = None # Stripe session URL can be useful

class CheckoutRequest(BaseModel):
    item_name: str
    price: float # Expect price in major currency unit (e.g., dollars)
    currency: str = 'usd'
    quantity: int = 1
    quote_id: Optional[str] = None # Optional: Pass quote ID for reference

class SimpleOrderItem(BaseModel):
    id: str
    name: str # e.g., file name or quote ID part
    quantity: int
    price: float # Price per item in major currency unit (e.g., dollars)

class PaymentIntentRequest(BaseModel):
    items: List[SimpleOrderItem]
    currency: str = 'usd'
    customer_email: Optional[str] = None # Optional: Collect email if needed
    # Add other fields you collect in your form, e.g., shipping, name
    metadata: Optional[Dict[str, str]] = None # To pass custom data


# --- API Endpoints ---

@app.get("/", tags=["General"])
async def get_root():
    """Returns basic API information."""
    available_processes = [p.value for p in PROCESSORS.keys()]
    return {
        "service": "Manufacturing Instant Quote API",
        "version": "1.2.0",
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
    quote_result_internal = None # To store the result before returning
    try:
        tmp_file_path = await save_upload_file_tmp(model_file)
        # DO NOT add cleanup to background tasks here if we need the file later

        processor = get_processor(process)
        logger.info(f"API: Calling generate_quote for {model_file.filename}, Process: {process}, Material: {material_id}")
        quote_result_internal: QuoteResult = processor.generate_quote(
            file_path=tmp_file_path,
            material_id=material_id
        )
        logger.info(f"API: Quote generated with ID {quote_result_internal.quote_id}, Status: {quote_result_internal.dfm_report.status}")

        # --- Store file path temporarily --- 
        # WARNING: Fragile in-memory storage
        if quote_result_internal.success and quote_result_internal.quote_id:
            temp_file_storage[quote_result_internal.quote_id] = tmp_file_path
            logger.info(f"Stored temp path {tmp_file_path} for quote {quote_result_internal.quote_id}")
            # Schedule cleanup ONLY IF payment doesn't happen (e.g., after a timeout)?
            # This is complex. For now, rely on webhook to trigger cleanup/upload.
        else:
             # If quote failed, clean up immediately
             logger.warning(f"Quote {quote_result_internal.quote_id} failed or missing ID. Cleaning up temp file {tmp_file_path} immediately.")
             # Use background task for immediate cleanup if quote fails
             background_tasks.add_task(cleanup_temp_file_and_storage, quote_result_internal.quote_id, tmp_file_path) 
             tmp_file_path = None # Prevent finally block from trying again

        return quote_result_internal

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
        logger.exception("Unexpected error during /quote endpoint processing:")
        # Ensure cleanup happens even on unexpected error IF quote ID wasn't generated/stored
        if tmp_file_path and (not quote_result_internal or not quote_result_internal.quote_id):
             background_tasks.add_task(cleanup_temp_file_and_storage, "unknown_quote", tmp_file_path)
        raise HTTPException(status_code=500, detail=f"An unexpected internal server error occurred: {e}")

# --- Optional: Add endpoint for LLM enhanced explanations ---
# @app.post("/quote/{quote_id}/enhanced-explanation", tags=["Quoting"])
# async def get_enhanced_explanation(quote_id: str):
#    # Requires storing quote results (e.g., in memory cache or DB)
#    # Fetch quote result
#    # If DFM issues exist and LLM API key is configured:
#    #   Call LLM service with issue details
#    #   Return enhanced explanation
#    raise HTTPException(status_code=501, detail="Not Implemented Yet")

@app.post("/create-checkout-session", response_model=CheckoutSessionResponse, tags=["Payments"])
async def create_checkout_session_endpoint(request_data: CheckoutSessionRequest):
    """Creates a Stripe Checkout Session, enabling shipping address collection."""
    if not stripe.api_key:
        logger.error("Attempted checkout session creation without Stripe key.")
        raise HTTPException(status_code=503, detail="Payment processing is not configured.")

    frontend_url = getattr(settings, 'frontend_url', 'http://localhost:3000')

    try:
        unit_amount_cents = int(request_data.price * 100)
        if unit_amount_cents <= 0:
            raise HTTPException(status_code=400, detail="Price must be positive.")
            
        # Check if shipping cost was provided
        shipping_cost = getattr(request_data, 'shipping_cost', None)
        
        # Create line items array, starting with the product
        line_items = [
            {
                'price_data': {
                    'currency': request_data.currency.lower(),
                    'product_data': {
                        'name': request_data.item_name,
                    },
                    'unit_amount': unit_amount_cents,
                },
                'quantity': request_data.quantity,
            },
        ]
        
        # Add shipping as a separate line item if provided
        if shipping_cost and shipping_cost > 0:
            shipping_amount_cents = int(shipping_cost * 100)
            line_items.append({
                'price_data': {
                    'currency': request_data.currency.lower(),
                    'product_data': {
                        'name': 'Shipping & Handling',
                    },
                    'unit_amount': shipping_amount_cents,
                },
                'quantity': 1,
            })
            logger.info(f"Adding shipping cost: ${shipping_cost:.2f} to checkout session")

        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            # Collect shipping address
            shipping_address_collection={
                'allowed_countries': ['US', 'CA'], # Specify allowed countries
            },
            success_url=f"{frontend_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/cart?cancelled=true",
            metadata={
                'quote_id': request_data.quote_id if request_data.quote_id else 'N/A',
                # Add file_name to metadata
                'file_name': request_data.file_name if request_data.file_name else 'N/A',
                # Add shipping cost to metadata
                'shipping_cost': str(shipping_cost) if shipping_cost else '0' 
            }
        )

        logger.info(f"Created Stripe Checkout Session: {checkout_session.id} for {request_data.item_name}")
        return CheckoutSessionResponse(sessionId=checkout_session.id, url=checkout_session.url)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Payment provider error: {getattr(e, 'user_message', str(e))}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Unexpected error creating checkout session:")
        raise HTTPException(status_code=500, detail="Internal server error creating checkout session.")

@app.post("/create-payment-intent", tags=["Payments"])
async def create_payment_intent(payment_request: PaymentIntentRequest):
    """Creates a Stripe Payment Intent based on cart items."""
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Payment processing is not configured.")

    try:
        # Calculate total amount from items
        # IMPORTANT: Ensure price calculation is secure and validated server-side
        # Never trust amounts sent directly from the client for the final charge.
        # Here we assume the prices in payment_request.items are trustworthy (e.g., fetched from quote results)
        total_amount_major_unit = sum(item.price * item.quantity for item in payment_request.items)
        if total_amount_major_unit <= 0:
             raise HTTPException(status_code=400, detail="Invalid order amount.")

        # Convert to smallest currency unit (e.g., cents)
        amount_in_cents = int(total_amount_major_unit * 100)

        # Prepare metadata
        metadata = payment_request.metadata or {}
        metadata['item_count'] = str(len(payment_request.items))
        metadata['first_item_id'] = payment_request.items[0].id if payment_request.items else 'N/A'
        # --- Add quote_id and file_name from request metadata ---
        # Ensure these are passed from the frontend in payment_request.metadata
        if 'quote_id' in metadata:
            logger.info(f"Adding quote_id {metadata.get('quote_id')} to PaymentIntent metadata.")
        else:
             logger.warning("quote_id not found in request metadata for PaymentIntent.")
             # We should still allow creation, but webhook might lack context
             metadata['quote_id'] = metadata.get('quote_id', 'MISSING') # Ensure key exists even if None initially

        if 'file_name' in metadata:
            logger.info(f"Adding file_name {metadata.get('file_name')} to PaymentIntent metadata.")
        else:
            logger.warning("file_name not found in request metadata for PaymentIntent.")
            metadata['file_name'] = metadata.get('file_name', 'MISSING') # Ensure key exists even if None initially
        # --------------------------------------------------------

        # Create Payment Intent
        intent_params = {
            'amount': amount_in_cents,
            'currency': payment_request.currency.lower(),
            'automatic_payment_methods': {'enabled': True},
            'metadata': metadata, # Metadata now includes quote_id and file_name if provided
        }
        if payment_request.customer_email:
            # Optional: Find/Create Stripe Customer for better tracking
            customers = stripe.Customer.list(email=payment_request.customer_email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                customer = stripe.Customer.create(email=payment_request.customer_email)
                customer_id = customer.id
            intent_params['customer'] = customer_id
            # Can also add description, shipping info here if needed

        payment_intent = stripe.PaymentIntent.create(**intent_params)

        logger.info(f"Created Payment Intent: {payment_intent.id} for amount {total_amount_major_unit:.2f} {payment_request.currency}")
        # Return the client secret to the frontend
        return {
            "clientSecret": payment_intent.client_secret,
            "paymentIntentId": payment_intent.id,
            "amount": total_amount_major_unit,
            "currency": payment_request.currency
            }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Payment provider error: {e}")
    except HTTPException as e: # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.exception("Unexpected error creating payment intent:")
        raise HTTPException(status_code=500, detail="Internal server error creating payment session.")


@app.post("/stripe-webhook", tags=["Payments"])
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks, stripe_signature: Optional[str] = Header(None)):
    """Handles webhooks, attempts file upload THEN sends Slack notification."""
    if not stripe.api_key or not settings.stripe_webhook_secret or not stripe_signature:
        logger.error("Webhook received with missing config/signature.")
        raise HTTPException(status_code=400, detail="Webhook configuration or signature missing.")

    payload = await request.body()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
        logger.info(f"Stripe webhook event received: {event['type']}")
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error constructing webhook event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing error")

    # Import datetime modules at the top level to avoid local variable errors
    from datetime import datetime, timezone, timedelta

    # --- Handle the payment_intent.succeeded event ---
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent.id
        
        # Create a session-specific logger for this payment
        session_logger = get_session_logger(f"payment_{payment_intent_id}")
        session_logger.info(f"===== PAYMENT SESSION START: {payment_intent_id} =====")
        session_logger.info(f"Webhook: Processing PaymentIntent succeeded: {payment_intent_id}")
        
        # Log the full payment intent for debugging (but redact sensitive info)
        pi_dict = payment_intent.to_dict()
        # Redact sensitive data before logging
        if 'client_secret' in pi_dict:
            pi_dict['client_secret'] = '[REDACTED]'
        session_logger.debug(f"Full payment intent data: {json.dumps(pi_dict, indent=2)}")
        
        # Check for Checkout Session information if available
        checkout_session = None
        try:
            # Try to retrieve the Checkout Session that created this PaymentIntent
            if hasattr(payment_intent, 'metadata') and 'checkout_session_id' in payment_intent.metadata:
                checkout_session_id = payment_intent.metadata['checkout_session_id']
                session_logger.info(f"Found checkout_session_id in metadata: {checkout_session_id}")
                checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
                session_logger.debug(f"Retrieved checkout session: {checkout_session.id}")
            else:
                # Try to find the checkout session by querying for this payment intent
                sessions = stripe.checkout.Session.list(
                    payment_intent=payment_intent_id,
                    limit=1
                )
                if sessions and sessions.data:
                    checkout_session = sessions.data[0]
                    session_logger.info(f"Found checkout session by query: {checkout_session.id}")
        except Exception as session_err:
            session_logger.error(f"Error retrieving checkout session: {session_err}")
        
        # Log the checkout session if found
        if checkout_session:
            session_logger.info(f"Checkout session details - ID: {checkout_session.id}, Customer email: {checkout_session.customer_details.email if checkout_session.customer_details else 'Not available'}")
            
            # Store important info in a cleaner way for later use
            if checkout_session.customer_details and checkout_session.customer_details.email:
                # Store customer email in payment intent metadata if not already there
                if 'receipt_email' not in pi_dict or not pi_dict['receipt_email']:
                    try:
                        stripe.PaymentIntent.modify(
                            payment_intent_id,
                            receipt_email=checkout_session.customer_details.email
                        )
                        session_logger.info(f"Updated payment intent with customer email: {checkout_session.customer_details.email}")
                    except Exception as update_err:
                        session_logger.error(f"Error updating payment intent with email: {update_err}")

        # --- Send Minimal Immediate Alert (keep this) ---
        try:
            from slack_sdk import WebClient as SyncWebClient
            slack_token = getattr(settings, 'slack_bot_token', os.getenv('SLACK_BOT_TOKEN'))
            channel_id = getattr(settings, 'slack_upload_channel_id', os.getenv('SLACK_UPLOAD_CHANNEL_ID'))
            if slack_token and channel_id:
                minimal_client = SyncWebClient(token=slack_token)
                minimal_client.chat_postMessage(
                    channel=channel_id,
                    text=f"⚠️ PAYMENT ALERT: Received payment with ID {payment_intent_id} - Processing full notification..."
                )
                session_logger.info("Sent initial payment alert to Slack")
            else:
                session_logger.warning("Could not send initial payment alert - missing token or channel")
        except Exception as minimal_error:
            session_logger.error(f"Unable to send minimal payment alert: {minimal_error}")
            
        # Initialize Slack blocks for notification
        slack_blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📦 New Manufacturing Order (Quote: Q-1745432819881)", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Payment Processed Successfully*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Order ID:* {payment_intent_id}"}, "block_id": "order_id_section"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Customer:* Not available"}, "block_id": "customer_section"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Shipping Address:*\nNot available"}, "block_id": "shipping_section"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Ordered Items:*\nProcessing..."}, "block_id": "ordered_items_section"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*PAYMENT:*\nProcessing..."}, "block_id": "payment_section"},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "Order processed automatically. Check attached files."}]}
        ]
        
        # Default fallback text for notifications
        slack_fallback_text = f"New manufacturing order received. Payment ID: {payment_intent_id}"

        # --- Extract Core Details ---
        base_quote_id = None
        all_quote_ids_str = None
        all_file_names_str = None
        model_files_to_upload = [] # Declare this outside try block so it's accessible in finally
        
        try:
            # Extract basic info
            amount_received = payment_intent.get('amount_received', 0) / 100.0
            currency = payment_intent.get('currency', 'usd').upper()
            customer_email = payment_intent.get('receipt_email') # Preferred source
            customer_name = None
            shipping_details = payment_intent.get('shipping')
            shipping_address_str = "Shipping address not provided via Stripe."
            
            # Extract metadata early to avoid scope issues
            metadata = payment_intent.get('metadata', {})
            session_logger.info(f"Metadata from payment intent: {metadata}")
            
            # IMPORTANT: Store order data in JSON file for order success page
            try:
                # Ensure storage directory exists
                import os
                import pathlib
                import json as json_lib
                
                # Use the top-level storage path from the project root, not the backend directory
                # The webhook runs from the backend/quote_system directory but we need to write to the project storage
                project_root = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
                storage_dir = pathlib.Path(os.path.join(project_root, 'storage', 'orders'))
                storage_dir.mkdir(parents=True, exist_ok=True)
                session_logger.info(f"Using storage directory for order data: {storage_dir}")
                
                # Get customer information
                # Use variables that were extracted earlier in the main try block
                local_customer_name = customer_name if 'customer_name' in locals() else None
                local_customer_email = customer_email if 'customer_email' in locals() else None
                
                if checkout_session and checkout_session.customer_details:
                    if hasattr(checkout_session.customer_details, 'name'):
                        local_customer_name = checkout_session.customer_details.name
                    if hasattr(checkout_session.customer_details, 'email'):
                        local_customer_email = checkout_session.customer_details.email
                
                if not local_customer_email and 'receipt_email' in pi_dict:
                    local_customer_email = pi_dict['receipt_email']
                
                # Get shipping address
                shipping_address = shipping_details.get('address', {}) if shipping_details else {}
                if not shipping_address and checkout_session and hasattr(checkout_session, 'shipping') and checkout_session.shipping:
                    shipping_address = checkout_session.shipping.address.to_dict() if hasattr(checkout_session.shipping, 'address') else {}
                
                # Get order items from metadata
                items = []
                quote_id = metadata.get('quote_id', 'Unknown')
                file_name = metadata.get('file_name', 'Unknown')
                material = metadata.get('material', 'Standard')
                quantity = metadata.get('quantity', '1')
                
                # Build basic item
                items.append({
                    'id': quote_id,
                    'name': file_name,
                    'fileName': file_name,
                    'price': amount_received,  # Total price
                    'quantity': int(quantity) if quantity.isdigit() else 1,
                    'material': material,
                    'process': metadata.get('process', 'Standard'),
                    'technology': metadata.get('technology', 'SLA')
                })
                
                # Create the order data object
                order_data = {
                    'paymentIntentId': payment_intent_id,
                    'customerName': local_customer_name or shipping_details.get('name', 'Unknown') if shipping_details else 'Unknown',
                    'customerEmail': local_customer_email or 'Unknown',
                    'totalAmount': amount_received,
                    'items': items,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'shippingAddress': shipping_address
                }
                
                # Save to both file names - one for payment intent ID and one for session ID
                # This ensures either ID will work in the success page
                
                # 1. Save with payment intent ID filename
                pi_file_path = storage_dir / f"{payment_intent_id}.json"
                with open(pi_file_path, 'w') as f:
                    json_lib.dump(order_data, f, indent=2)
                session_logger.info(f"Saved order data to file: {pi_file_path}")
                
                # 2. Save with checkout session ID filename if available
                if checkout_session:
                    session_file_path = storage_dir / f"{checkout_session.id}.json"
                    with open(session_file_path, 'w') as f:
                        json_lib.dump(order_data, f, indent=2)
                    session_logger.info(f"Saved order data to file: {session_file_path}")
                    
                session_logger.info("Successfully stored order data for success page")
            except Exception as storage_err:
                session_logger.error(f"Error storing order data JSON: {storage_err}", exc_info=True)
            
            # Get customer information from all possible sources
            # 1. Try to get from payment intent directly
            if not customer_email:
                customer_email = metadata.get('customerEmail', metadata.get('email'))
                session_logger.info(f"Retrieved customer email from metadata: {customer_email}")
            
            # 2. Try to get from Checkout Session if available
            if checkout_session:
                session_logger.info("Looking for customer email in checkout session")
                if hasattr(checkout_session, 'customer_details') and checkout_session.customer_details:
                    if not customer_email and checkout_session.customer_details.email:
                        customer_email = checkout_session.customer_details.email
                        session_logger.info(f"Found customer email in checkout session: {customer_email}")
                    
                    # Get customer name from checkout session if possible
                    if (not customer_name or customer_name == 'N/A') and checkout_session.customer_details.name:
                        customer_name = checkout_session.customer_details.name
                        session_logger.info(f"Found customer name in checkout session: {customer_name}")
                
                # Try to get shipping address from checkout session
                if hasattr(checkout_session, 'shipping') and checkout_session.shipping:
                    session_logger.info("Found shipping details in checkout session")
                    checkout_shipping = checkout_session.shipping
                    
                    if hasattr(checkout_shipping, 'address') and checkout_shipping.address:
                        addr = checkout_shipping.address
                        line1 = getattr(addr, 'line1', '')
                        line2 = getattr(addr, 'line2', None)
                        city = getattr(addr, 'city', '')
                        state = getattr(addr, 'state', '')
                        postal_code = getattr(addr, 'postal_code', '')
                        country = getattr(addr, 'country', '')
                        
                        address_lines = [line1] + ([line2] if line2 else []) + [f"{city}, {state} {postal_code}", country]
                        shipping_address_str = "\n".join(filter(None, address_lines))
                        session_logger.info(f"Built shipping address from checkout session")
            
            # 3. Get name/address from payment intent shipping if still needed
            if shipping_details:
                if not customer_name or customer_name == 'N/A':
                    customer_name = shipping_details.get('name', 'N/A')
                    session_logger.info(f"Using customer name from payment intent shipping: {customer_name}")
                
                if not customer_email:
                    customer_email = shipping_details.get('email')
                    session_logger.info(f"Using customer email from payment intent shipping: {customer_email}")
                
                # Only use shipping address from payment intent if we don't have one from checkout session
                if shipping_address_str == "Shipping address not provided via Stripe.":
                    addr = shipping_details.get('address')
                    if addr:
                        line1 = addr.get('line1', '')
                        line2 = addr.get('line2')
                        city = addr.get('city', '')
                        state = addr.get('state', '')
                        postal_code = addr.get('postal_code', '')
                        country = addr.get('country', '')
                        address_lines = [line1] + ([line2] if line2 else []) + [f"{city}, {state} {postal_code}", country]
                        shipping_address_str = " ".join(filter(None, address_lines))
                        session_logger.info(f"Built shipping address from payment intent shipping")
            
            customer_name = customer_name or 'N/A' # Ensure customer_name is set
            customer_display = f"{customer_name}" + (f" ({customer_email})" if customer_email else "")

            # --- Extract Base Quote ID from metadata --- 
            session_logger.info(f"Processing quote IDs from metadata: {metadata}")
            
            # Check for Checkout Session metadata if we have a session
            checkout_metadata = {}
            if checkout_session:
                checkout_metadata = checkout_session.get('metadata', {})
                session_logger.info(f"Metadata from checkout session: {checkout_metadata}")
                
                # Merge checkout metadata into our metadata, prioritizing checkout session
                if checkout_metadata:
                    # Create a combined metadata dictionary
                    metadata = {**metadata, **checkout_metadata}
                    session_logger.info(f"Combined metadata from both sources: {metadata}")
            
            # Enhanced quote ID extraction
            # Look for cart metadata that might be JSON encoded
            cart_item_ids = None
            quote_ids = None
            base_quote_id = None
            
            # Try to extract from cartItemIds or quoteIds (JSON arrays)
            try:
                if 'cartItemIds' in metadata:
                    cart_item_ids = json.loads(metadata.get('cartItemIds', '[]'))
                    session_logger.info(f"Found cart item IDs in metadata: {cart_item_ids}")
                if 'quoteIds' in metadata:
                    quote_ids = json.loads(metadata.get('quoteIds', '[]'))
                    session_logger.info(f"Found quote IDs in metadata: {quote_ids}")
            except json.JSONDecodeError as json_err:
                session_logger.error(f"Error parsing JSON metadata: {json_err}")
            
            # Try all possible sources for quote IDs, in order of preference
            all_quote_ids_str = None
            
            # 1. Try quoteIds JSON array first
            if quote_ids and isinstance(quote_ids, list) and len(quote_ids) > 0:
                all_quote_ids_str = ','.join(quote_ids)
                session_logger.info(f"Using quote IDs from quoteIds JSON: {all_quote_ids_str}")
            
            # 2. Try cartItemIds JSON array next (which may contain quote IDs)
            elif cart_item_ids and isinstance(cart_item_ids, list) and len(cart_item_ids) > 0:
                # Filter only items that look like quote IDs (starting with Q-)
                quote_items = [item for item in cart_item_ids if isinstance(item, str) and item.startswith('Q-')]
                if quote_items:
                    all_quote_ids_str = ','.join(quote_items)
                    session_logger.info(f"Using quote IDs from cartItemIds JSON: {all_quote_ids_str}")
            
            # 3. Try all_quote_ids string
            if not all_quote_ids_str:
                all_quote_ids_str = metadata.get('all_quote_ids')
                if all_quote_ids_str:
                    session_logger.info(f"Using quote IDs from all_quote_ids string: {all_quote_ids_str}")
            
            # 4. Try comma-separated quote_id (some implementations put multiple IDs in this field)
            if not all_quote_ids_str:
                single_quote_id = metadata.get('quote_id')
                if single_quote_id and ',' in single_quote_id:
                    all_quote_ids_str = single_quote_id
                    session_logger.info(f"Using comma-separated quote IDs from quote_id field: {all_quote_ids_str}")
            
            # 5. Fall back to single quote_id
            if not all_quote_ids_str:
                single_quote_id = metadata.get('quote_id')
                if single_quote_id and single_quote_id not in ['N/A', 'MISSING', None, '']:
                    all_quote_ids_str = single_quote_id
                    session_logger.info(f"Using single quote ID from quote_id field: {all_quote_ids_str}")
            
            # Get corresponding filenames if available
            all_file_names_str = metadata.get('all_file_names', metadata.get('file_name', 'Unknown Filename'))
            
            # Process quote IDs to extract base quote ID
            if all_quote_ids_str:
                quote_id_list = [qid.strip() for qid in all_quote_ids_str.split(',') if qid.strip()]
                if quote_id_list:
                    # Use the first ID to determine the base ID
                    first_quote_id = quote_id_list[0]
                    base_quote_id = get_base_quote_id_py(first_quote_id) # Use Python helper
                    session_logger.info(f"Extracted base_quote_id '{base_quote_id}' from quote IDs: {all_quote_ids_str}")
                else:
                    session_logger.warning("Quote IDs string was present but empty.")
            
            # Fallback: Regex search in description (less reliable)
            if not base_quote_id:
                description = payment_intent.get('description', '')
                if description and 'Q-' in description:
                    quote_match = re.search(r'(Q-[0-9]+)', description) # Find first Q-ID
                    if quote_match:
                        extracted_id = quote_match.group(0)
                        base_quote_id = get_base_quote_id_py(extracted_id) # Use Python helper
                        session_logger.info(f"Extracted base_quote_id '{base_quote_id}' from PI description: {description}")
                        # Assume single item if found this way
                        if not all_quote_ids_str: all_quote_ids_str = extracted_id
                        if not all_file_names_str: all_file_names_str = 'Unknown Filename (from description)'
            
            # Last resort: Look in storage/fff-configs directory for recent configs
            if not base_quote_id:
                try:
                    session_logger.info("Attempting to find quote IDs from recent FFF configs")
                    fff_config_dir = project_root / "storage" / "fff-configs"
                    if fff_config_dir.exists() and fff_config_dir.is_dir():
                        # Find the most recently modified .json files
                        config_files = sorted(
                            [f for f in fff_config_dir.iterdir() if f.is_file() and f.name.endswith('.json')],
                            key=lambda f: f.stat().st_mtime,
                            reverse=True  # Most recent first
                        )
                        
                        # Check the first few files (most recent)
                        for config_file in config_files[:5]:  # Check up to 5 most recent
                            # Extract quote ID from filename (assuming format like Q-123456789.json)
                            if config_file.name.startswith('Q-'):
                                quote_id_from_config = config_file.name.split('.')[0]
                                base_quote_id = get_base_quote_id_py(quote_id_from_config)
                                all_quote_ids_str = quote_id_from_config
                                session_logger.info(f"Found quote ID from recent config file: {quote_id_from_config}")
                                break
                except Exception as config_err:
                    session_logger.error(f"Error searching for configs: {config_err}")

            # If all else fails, use a generated ID as last resort
            if not base_quote_id:
                session_logger.error(f"CRITICAL: Could not determine base_quote_id for payment {payment_intent_id}. Metadata: {metadata}")
                # Create a fallback ID that's at least identifiable for this payment
                base_quote_id = f"UNKNOWN_ORDER_{payment_intent_id[-6:]}"
                all_quote_ids_str = base_quote_id
                all_file_names_str = "Unknown Filename"
                session_logger.info(f"Using generated fallback quote ID: {base_quote_id}")
            
            # --- Get Order Timestamp (PST) --- 
            try:
                created_ts = payment_intent.created
                utc_time = datetime.fromtimestamp(created_ts, tz=timezone.utc)
                pst_offset = timedelta(hours=-7) # Assuming PDT for now
                pst_time = utc_time.astimezone(timezone(pst_offset))
                pst_time_str = pst_time.strftime('%B %d, %Y, %I:%M %p')
            except Exception as dt_error:
                logger.error(f"Error formatting PST time: {dt_error}")
                pst_time_str = "Unknown time (PST)"

            # Update Slack blocks with order header info
            for block in slack_blocks:
                if block.get("type") == "header":
                    block["text"]["text"] = f"📦 New Manufacturing Order (Quote: {base_quote_id})"
                elif block.get("block_id") == "customer_section":
                    block["text"]["text"] = f"*Customer:* {customer_display}"
                elif block.get("block_id") == "shipping_section":
                    block["text"]["text"] = f"*Shipping Address:*\n{shipping_address_str}"
                elif block.get("block_id") == "payment_section":
                    block["text"]["text"] = f"*PAYMENT:* ${amount_received:.2f} {currency} (Order Date: {pst_time_str})"

            # --- Find or Create Order Folder (Step 2b) --- 
            order_folder_path_str = find_order_folder_py(base_quote_id, payment_intent_id)
            order_folder_path = Path(order_folder_path_str) if order_folder_path_str else None
            if not order_folder_path:
                logger.error(f"Could not find or create order folder for base_quote_id: {base_quote_id} and payment_intent_id: {payment_intent_id}. Cannot process items or attach files.")
                # Decide how to proceed - maybe send basic notification without items/files?
            
            # --- Process Items & Files (Step 2c) --- 
            items_ordered_text = "" # Build this string
            model_files_to_upload = [] # List of dicts: {'path': str, 'name': str}
            processed_items_details = [] # List to store details for Slack formatting
            
            # Get list of all quote folders that might contain files for this order
            quote_ids = [qid.strip() for qid in (all_quote_ids_str or "").split(',') if qid.strip()]
            session_logger.info(f"Processing files for quote IDs: {quote_ids}")
            
            # First, create a list of all model files that need to be moved to the order folder
            files_to_move = []
            
            # 1. Check if order folder exists before proceeding with folder operations
            if order_folder_path and order_folder_path.is_dir():
                session_logger.info(f"Processing files for order folder: {order_folder_path}")
                
                # Start a comprehensive search for all relevant model files
                models_dir = Path(order_folder_path.parent)
                session_logger.info(f"Scanning models directory: {models_dir}")
                
                # Track all files with matching quote IDs
                quote_matching_files = []
                
                # A. SEARCH BY QUOTE ID MATCH (most reliable)
                # Look for files with matching quote IDs in root models directory
                session_logger.info("SEARCH PHASE 1: Finding files with matching quote IDs")
                for item in models_dir.iterdir():
                    if item == order_folder_path:
                        continue  # Skip the order folder itself
                    
                    # For files in root directory, check name patterns
                    if item.is_file():
                        file_matched = False
                        # Match patterns like "Q-1234567890_file.stl" or "Q-1234567890-A_file.stl"
                        for quote_id in quote_ids:
                            if (item.name.startswith(f"{quote_id}_") or 
                                item.name.startswith(f"{quote_id}-")):
                                quote_matching_files.append(item)
                                file_matched = True
                                session_logger.info(f"Found file matching quote ID {quote_id}: {item.name}")
                                break
                        
                        # We no longer check for recency, only exact quote ID matches
                        if not file_matched:
                            session_logger.debug(f"File {item.name} did not match any quote IDs")
                
                # B. SEARCH IN QUOTE-SPECIFIC FOLDERS
                session_logger.info("SEARCH PHASE 2: Checking quote-specific folders")
                for quote_id in quote_ids:
                    # Look for folders like Q-1234567890-04-23-2025--17-26-57
                    quote_folders = [
                        d for d in models_dir.iterdir() 
                        if d.is_dir() and (
                            d.name.startswith(f"{quote_id}-") or  # Starts with quote ID
                            d.name.startswith(f"{base_quote_id}-")  # Starts with base quote ID
                        ) and d != order_folder_path  # Not the order folder itself
                    ]
                    
                    session_logger.info(f"Found {len(quote_folders)} potential quote folders for {quote_id}")
                    
                    for quote_folder in quote_folders:
                        session_logger.info(f"Scanning quote folder: {quote_folder.name}")
                        for item in quote_folder.iterdir():
                            if item.is_file() and not item.name.endswith('.metadata.json'):
                                ext = item.name.split('.')[-1].lower()
                                if ext in ['stl', 'step', 'stp', 'obj']:
                                    quote_matching_files.append(item)
                                    session_logger.info(f"Found model file in quote folder: {item.name}")
                
                # We're removing the time-based search to avoid including unrelated files
                # We'll only use explicit quote ID matching instead
                session_logger.info("SEARCH PHASE 3: Phase skipped - only using exact quote ID matches")
                
                # No additional files will be added from time-based searches
                session_logger.info(f"Using only files that match quote IDs: {quote_ids} (found {len(quote_matching_files)} so far)")
                
                # 2. PREPARE FILES TO MOVE TO ORDER FOLDER
                session_logger.info(f"Building file move list from {len(quote_matching_files)} quote matches")
                
                # Add all quote-matching files to the move list
                for item in quote_matching_files:
                    dest_path = order_folder_path / item.name
                    if item.parent != order_folder_path:  # Not already in order folder
                        files_to_move.append({
                            'src_path': item,
                            'dest_path': dest_path,
                            'priority': 'high',  # Quote-matched files are high priority
                            'type': 'quote_match'
                        })
                        
                        # If there's a metadata file, also move it
                        metadata_path = item.with_suffix(item.suffix + '.metadata.json')
                        if metadata_path.exists():
                            files_to_move.append({
                                'src_path': metadata_path,
                                'dest_path': order_folder_path / metadata_path.name,
                                'priority': 'high',
                                'type': 'metadata'
                            })
                
                # We're no longer adding recent model files based on timestamps
                # Only using explicit quote ID matching
                
                # 3. MOVE FILES TO ORDER FOLDER
                session_logger.info(f"Moving {len(files_to_move)} files to order folder")
                
                # Process files by priority
                for priority in ['high', 'medium']:
                    priority_files = [f for f in files_to_move if f.get('priority') == priority]
                    session_logger.info(f"Processing {len(priority_files)} {priority} priority files")
                    
                    for file_item in priority_files:
                        try:
                            # Copy file to destination
                            if not file_item['dest_path'].exists():
                                shutil.copy2(file_item['src_path'], file_item['dest_path'])
                                session_logger.info(f"Copied {file_item['type']} file {file_item['src_path'].name} to order folder")
                                
                                # Don't delete original files for safety
                                # Instead, just leave them in place
                            else:
                                session_logger.info(f"File {file_item['dest_path'].name} already exists in order folder")
                        except Exception as copy_err:
                            session_logger.error(f"Error copying file {file_item['src_path']}: {copy_err}")
                
                # 4. PROCESS ALL FILES IN ORDER FOLDER
                session_logger.info("Processing all files in order folder for Slack notification")
                all_items_in_folder = list(order_folder_path.iterdir())
                
                # Get all model files (excluding metadata files)
                model_files_in_folder = [
                    item for item in all_items_in_folder 
                    if item.is_file() and not item.name.endswith('.metadata.json')
                    and item.name.lower().endswith(('.stl', '.step', '.stp', '.obj'))
                ]
                
                session_logger.info(f"Found {len(model_files_in_folder)} model files in order folder")
                
                # Process all model files in the order folder
                for item_path in model_files_in_folder:
                    # Try to read corresponding metadata file
                    metadata_content = None
                    metadata_path = item_path.with_suffix(item_path.suffix + '.metadata.json')
                    
                    # Try both direct metadata file and alternative formats
                    metadata_paths = [
                        metadata_path,  # Standard: filename.stl.metadata.json
                        Path(str(metadata_path).replace('.metadata.json', '_metadata.json')),  # Alternative: filename_metadata.json
                        Path(f"{metadata_path.parent}/{metadata_path.stem}_metadata.json")  # Another alternative: filename.stl_metadata.json
                    ]
                    
                    for meta_path in metadata_paths:
                        if meta_path.exists():
                            try:
                                with open(meta_path, 'r') as f:
                                    metadata_content = json.load(f)
                                    session_logger.info(f"Found metadata at {meta_path}")
                                    break
                            except Exception as json_err:
                                session_logger.error(f"Error reading metadata file {meta_path}: {json_err}")
                    
                    # If no metadata file found, try to infer from filename
                    if not metadata_content:
                        session_logger.info(f"No metadata found for {item_path.name}, inferring from filename")
                        metadata_content = {}
                        
                        # Check if filename contains a quote ID
                        filename_quote_id = None
                        for quote_id in quote_ids:
                            if quote_id in item_path.name:
                                filename_quote_id = quote_id
                                break
                        
                        if filename_quote_id:
                            metadata_content['quoteId'] = filename_quote_id
                    
                    # Extract details with fallbacks
                    item_file_name = item_path.name
                    # Try to parse quantity as an integer from metadata
                    try:
                        quantity_str = metadata_content.get('quantity', '1') if metadata_content else '1'
                        # Handle both string and numeric values
                        if isinstance(quantity_str, str) and quantity_str.strip():
                            quantity = int(quantity_str)
                        elif isinstance(quantity_str, (int, float)):
                            quantity = int(quantity_str)
                        else:
                            quantity = 1
                    except (ValueError, TypeError):
                        quantity = 1
                    session_logger.info(f"Parsed quantity for {item_path.name}: {quantity}")
                    technology = metadata_content.get('technology', metadata_content.get('process', 'Unknown')) if metadata_content else 'Unknown'
                    material = metadata_content.get('material', 'Unknown') if metadata_content else 'Unknown'
                    notes = metadata_content.get('specialInstructions', metadata_content.get('notes', '')) if metadata_content else ''
                    suffixed_quote_id = metadata_content.get('quoteId', metadata_content.get('quote_id', 'Unknown')) if metadata_content else 'Unknown'
                    
                    # For items missing quote ID, try to infer from filename
                    if suffixed_quote_id == 'Unknown':
                        for quote_id in quote_ids:
                            if quote_id in item_path.name:
                                suffixed_quote_id = quote_id
                                break
                        # If still unknown, use the base quote ID
                        if suffixed_quote_id == 'Unknown':
                            suffixed_quote_id = base_quote_id
                    
                    # Add to processed items list
                    processed_items_details.append({
                        'quantity': quantity,
                        'fileName': item_file_name,
                        'technology': technology,
                        'material': material,
                        'notes': notes,
                        'suffixed_quote_id': suffixed_quote_id
                    })
                    
                    # Add to upload list
                    model_files_to_upload.append({
                        'path': str(item_path), 
                        'name': item_file_name,
                        'quote_id': suffixed_quote_id,
                        'metadata': metadata_content
                    })
                    
                    session_logger.info(f"Processed model file: {item_file_name} (Quote ID: {suffixed_quote_id}, Technology: {technology}, Material: {material})")
            else:
                # Order folder doesn't exist or couldn't be created
                session_logger.error(f"Order folder missing or invalid: {order_folder_path}")
            
            # We're removing the desperate search since it can lead to incorrect file matching
            # Instead, we'll only trust explicit quote ID matches
            if not model_files_to_upload:
                session_logger.warning("No files found matching the quote IDs for this order. Will proceed without model files.")
                
                # Log this as a warning so we can investigate if needed
                session_logger.warning(f"Quote IDs that didn't match any files: {quote_ids}")
                session_logger.warning(f"Base quote ID with no matches: {base_quote_id}")
                
                # Create fallback item details from metadata if available
                if metadata and 'file_name' in metadata:
                    session_logger.info(f"Creating fallback item details from payment metadata")
                    # Use checkout metadata to create fallback items
                    fallback_file_name = metadata.get('file_name', 'Unknown Filename')
                    fallback_technology = metadata.get('technology', 'SLA')
                    fallback_material = metadata.get('material', 'Standard')
                    fallback_quantity = int(metadata.get('quantity', '1')) if metadata.get('quantity', '1').isdigit() else 1
                    fallback_notes = metadata.get('description', '')
                    
                    # Add to processed items list as fallback
                    processed_items_details.append({
                        'quantity': fallback_quantity,
                        'fileName': fallback_file_name,
                        'technology': fallback_technology,
                        'material': fallback_material,
                        'notes': fallback_notes,
                        'suffixed_quote_id': base_quote_id
                    })
                    
                    session_logger.info(f"Added fallback item from metadata: {fallback_file_name} ({fallback_technology}, {fallback_material})")
                    
                    # Create a placeholder temp file to attach to Slack
                    try:
                        import tempfile
                        placeholder_path = Path(tempfile.gettempdir()) / f"{base_quote_id}_placeholder.txt"
                        with open(placeholder_path, 'w') as f:
                            f.write(f"UPLOAD ERROR: The original file '{fallback_file_name}' could not be found.\n\n")
                            f.write(f"Technology: {fallback_technology}\n")
                            f.write(f"Material: {fallback_material}\n")
                            f.write(f"Quantity: {fallback_quantity}\n")
                            f.write(f"Quote ID: {base_quote_id}\n\n")
                            f.write("IMPORTANT: Please ask the customer to provide the model file again.")
                        
                        # Add this placeholder to the files to upload list
                        model_files_to_upload.append({
                            'path': str(placeholder_path),
                            'name': f"PLACEHOLDER_{fallback_file_name}",
                            'quote_id': base_quote_id,
                            'metadata': {
                                'technology': fallback_technology,
                                'material': fallback_material,
                                'quantity': fallback_quantity,
                                'error': 'Original file not found'
                            },
                            'is_placeholder': True
                        })
                        session_logger.info(f"Created placeholder file for Slack attachment: {placeholder_path}")
                    except Exception as placeholder_err:
                        session_logger.error(f"Error creating placeholder file: {placeholder_err}")
            
            # --- Format Slack Item Details (Step 2d) --- 
            if processed_items_details:
                items_text_parts = []
                for idx, item in enumerate(processed_items_details):
                    tech = item['technology']
                    display_tech = f"{tech} (3D Printing)" if tech in {'SLS', 'SLA', 'FDM'} else tech
                    part_text = (
                        f"{idx + 1}. {item['fileName']}\n"
                        f"         - Quantity: {item['quantity']}\n"
                        f"         - Technology: {display_tech}\n"
                        f"         - Material: {item['material']}"
                    )
                    if item['notes']:
                        part_text += f"\n         - Notes: {item['notes']}"
                    items_text_parts.append(part_text)
                items_ordered_text = "\n\n".join(items_text_parts)
                session_logger.info(f"Formatted details for {len(processed_items_details)} items")
            else:
                # Add a more detailed error message when no item details are found
                items_ordered_text = (
                    "⚠️ No valid item details found in order folder or metadata.\n\n"
                    f"Quote ID(s): {all_quote_ids_str}\n"
                    f"File Name(s): {all_file_names_str}\n\n"
                    "⚠️ ACTION REQUIRED: Please ask customer to re-upload model files."
                )
                session_logger.error(f"Could not process item details for order {base_quote_id}")
            
            # Update all the Slack blocks
            for block in slack_blocks:
                if block.get("type") == "header":
                    block["text"]["text"] = f"📦 New Manufacturing Order (Quote: {base_quote_id})"
                elif block.get("block_id") == "customer_section":
                    # Include email in customer section if available
                    if customer_email:
                        block["text"]["text"] = f"*Customer:* {customer_name}\n*Email:* {customer_email}"
                    else:
                        block["text"]["text"] = f"*Customer:* {customer_name}"
                elif block.get("block_id") == "shipping_section":
                    block["text"]["text"] = f"*Shipping Address:*\n{shipping_address_str}"
                elif block.get("block_id") == "payment_section":
                    block["text"]["text"] = f"*PAYMENT:* ${amount_received:.2f} {currency} (Order Date: {pst_time_str})"
                elif block.get("block_id") == "ordered_items_section":
                    block["text"]["text"] = f"*Ordered Items:*\n{items_ordered_text}"
            
            # Add debug information to Slack message for troubleshooting
            payment_debug_info = {
                "session_id": f"payment_{payment_intent_id}",
                "base_quote_id": base_quote_id,
                "all_quote_ids": all_quote_ids_str,
                "email_found": customer_email is not None,
                "files_found": len(model_files_to_upload),
                "log_file": f"logs/payment_{payment_intent_id}_*.log"
            }
            
            # # Add a hidden debug context block at the end of message
            # slack_blocks.append({
            #     "type": "context",
            #     "elements": [
            #         {
            #             "type": "mrkdwn",
            #             "text": f"Debug: `{json.dumps(payment_debug_info)}`"
            #         }
            #     ]
            # })
             
        except Exception as processing_error:
            logger.error(f"Critical error processing payment webhook details for {payment_intent_id}: {processing_error}", exc_info=True)
            # Send emergency notification
            slack_blocks = [
                {"type": "header", "text": {"type": "plain_text", "text": "🚨 URGENT: Payment Received with Processing Error", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"A payment ({payment_intent_id}) was received but there was an error processing the details.\n\nPlease check the server logs immediately and manually handle this order! Error: {processing_error}"}} 
            ]
            slack_fallback_text = f"URGENT: Payment {payment_intent_id} received but processing failed. Check server logs!"
            # Ensure we don't try to upload files if core processing failed
            model_files_to_upload = [] 

        # --- Send Final Slack Notification (consolidated for entire order) --- 
        try:
            session_logger.info(f"Sending consolidated notification for order {payment_intent_id} (Quote: {base_quote_id or 'UNKNOWN'})")
            slack_token = getattr(settings, 'slack_bot_token', os.getenv('SLACK_BOT_TOKEN'))
            channel_id = getattr(settings, 'slack_upload_channel_id', os.getenv('SLACK_UPLOAD_CHANNEL_ID'))
            
            if not slack_token or not channel_id:
                session_logger.error("Missing Slack token or channel ID")
            else:
                slack_client = SyncWebClient(token=slack_token)
                
                # First, prepare a consolidated message with all item details
                message_response = slack_client.chat_postMessage(
                    channel=channel_id,
                    blocks=slack_blocks, # Use the updated blocks with all item details
                    text=slack_fallback_text
                )
                
                session_logger.info(f"Slack message sent successfully, ts: {message_response.get('ts')}")
                
                # If message was successful, upload all model files as thread replies
                if message_response.get('ok') and model_files_to_upload:
                    thread_ts = message_response.get('ts')
                    session_logger.info(f"Uploading {len(model_files_to_upload)} model files as thread replies")
                    
                    # Group the model files by their type (like .stl, .step, etc.)
                    file_types = {}
                    for info in model_files_to_upload:
                        ext = info['name'].split('.')[-1].lower()
                        if ext not in file_types:
                            file_types[ext] = []
                        file_types[ext].append(info)
                    
                    # Log file types we're uploading
                    session_logger.info(f"File types to upload: {list(file_types.keys())}")
                    for ext, files in file_types.items():
                        session_logger.info(f"Found {len(files)} {ext} files to upload")
                    
                    # Keep count of successful uploads
                    successful_uploads = 0
                    
                    for model_file_info in model_files_to_upload:
                        file_path = model_file_info['path']
                        upload_name = model_file_info['name']
                        metadata = model_file_info.get('metadata', {})
                        quote_id = model_file_info.get('quote_id', base_quote_id)
                        
                        # Create a descriptive comment for this file
                        file_comment = f"File: {upload_name}"
                        if metadata:
                            if metadata.get('technology') or metadata.get('process'):
                                tech = metadata.get('technology', metadata.get('process', 'Unknown'))
                                file_comment += f"\nTechnology: {tech}"
                            if metadata.get('material'):
                                file_comment += f"\nMaterial: {metadata.get('material')}"
                            if metadata.get('quantity'):
                                file_comment += f"\nQuantity: {metadata.get('quantity')}"
                        
                        try:
                            if not os.path.exists(file_path):
                                session_logger.error(f"File path does not exist: {file_path}")
                                continue # Skip this file
                            
                            file_size = os.path.getsize(file_path)
                            if file_size == 0:
                                session_logger.warning(f"Skipping empty file: {upload_name} ({file_path})")
                                continue # Skip empty file
                            
                            # Read file into memory
                            with open(file_path, 'rb') as file_content:
                                file_data = file_content.read()
                            
                            session_logger.info(f"Uploading {upload_name} ({file_size} bytes)")
                            
                            # Determine file type for Slack
                            ext = upload_name.split('.')[-1].lower()
                            filetype = 'binary'  # Default for 3D files
                            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                                filetype = 'image/' + ext
                            
                            # Upload as a thread reply to the main message
                            upload_response = slack_client.files_upload_v2(
                                file=file_data,
                                filename=upload_name,
                                filetype=filetype,
                                channel=channel_id,
                                thread_ts=thread_ts,
                                initial_comment=file_comment
                            )
                            
                            if upload_response.get('ok'):
                                session_logger.info(f"Successfully uploaded {upload_name}")
                                successful_uploads += 1
                            else:
                                session_logger.error(f"Error uploading {upload_name}: {upload_response.get('error', 'Unknown Slack API Error')}")
                            
                        except Exception as upload_err:
                            session_logger.error(f"Exception uploading {upload_name}: {upload_err}", exc_info=True)
                else:
                    session_logger.warning(f"No files to upload or message failed")
        except Exception as slack_final_error:
            session_logger.error(f"Unexpected error during final Slack notification: {slack_final_error}", exc_info=True)

    # --- Handle other event types --- 
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Create a logger for failed payment
        failed_logger = get_session_logger(f"failed_{payment_intent.id}")
        failed_logger.warning(f"PaymentIntent failed: {payment_intent.id}. Reason: {payment_intent.get('last_payment_error', {}).get('message')}")
        
        # Extract and log error details
        error_detail = payment_intent.get('last_payment_error', {})
        if error_detail:
            failed_logger.error(f"Payment error details: {json.dumps(error_detail, default=str)}")
            
            # Also log customer email if available
            if 'payment_method' in error_detail and 'billing_details' in error_detail['payment_method']:
                email = error_detail['payment_method']['billing_details'].get('email')
                if email:
                    failed_logger.info(f"Customer email from failed payment: {email}")
    else:
        logger.info(f"Unhandled event type: {event['type']}")

    return JSONResponse(content={"received": True})

# =============================================
# Utility Functions (like get_base_quote_id_py)
# Can be in a separate utils.py or here
# =============================================

def get_base_quote_id_py(suffixed_quote_id: Optional[str]) -> Optional[str]:
    """Extracts the base quote ID from a potentially suffixed ID (Python version)."""
    if not suffixed_quote_id:
        return None
    parts = suffixed_quote_id.split('-')
    # Check if the last part looks like a single uppercase letter suffix
    if len(parts) > 2 and len(parts[-1]) == 1 and 'A' <= parts[-1] <= 'Z':
        return '-'.join(parts[:-1])
    # Otherwise, assume it's already the base ID
    return suffixed_quote_id

# --- Run Instruction (for direct execution, though usually run with uvicorn command) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server via __main__ (use 'uvicorn main_api:app --reload' for development)")
    uvicorn.run(app, host="0.0.0.0", port=8000) 