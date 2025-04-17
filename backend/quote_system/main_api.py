# main_api.py

import os
import time
import logging
import tempfile
import json # For Slack payload
import requests # For Slack notification
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

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
import asyncio # For background file cleanup/upload task
from slack_sdk.web.async_client import AsyncWebClient # Use AsyncWebClient

# Initial setup
logger = logging.getLogger(__name__)

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
    version="1.1.0",
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
        "version": "1.1.0",
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

        checkout_session = stripe.checkout.Session.create(
            line_items=[
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
            ],
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
                'file_name': request_data.file_name if request_data.file_name else 'N/A' 
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

    # --- Handle the payment_intent.succeeded event ---
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"Webhook: PaymentIntent succeeded: {payment_intent.id}")

        # Extract details
        amount_received = payment_intent.get('amount_received', 0) / 100.0
        currency = payment_intent.get('currency', 'usd').upper()
        payment_intent_id = payment_intent.id
        customer_email = payment_intent.get('receipt_email') or payment_intent.get('shipping', {}).get('email')
        customer_name = payment_intent.get('shipping', {}).get('name', 'N/A')
        shipping_details = payment_intent.get('shipping')
        shipping_address_str = "Shipping address not provided via Stripe."
        if shipping_details and shipping_details.get('address'):
             addr = shipping_details['address']
             line1 = addr.get('line1', '')
             line2 = addr.get('line2') # Get line2, might be None
             city = addr.get('city', '')
             state = addr.get('state', '')
             postal_code = addr.get('postal_code', '')
             country = addr.get('country', '')
             
             # Build address string line by line, handling potential None for line2
             address_lines = [line1]
             if line2: # Only add line2 if it's not None or empty
                 address_lines.append(line2)
             address_lines.append(f"{city}, {state} {postal_code}")
             address_lines.append(country)
             
             shipping_address_str = "\n".join(filter(None, address_lines)) # Join non-empty lines
        
        metadata = payment_intent.get('metadata', {})
        quote_id = metadata.get('quote_id')
        file_name = metadata.get('file_name', 'Unknown Filename')
        received_timestamp = datetime.fromtimestamp(payment_intent.created, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')

        # --- Construct Slack Message Blocks ---
        # Use single \n for mrkdwn newlines
        slack_blocks = [
             {"type": "header", "text": {"type": "plain_text", "text": ":package: New Order Ready for Fulfillment!", "emoji": True}},
             {"type": "section", "fields": [
                 {"type": "mrkdwn", "text": f"*Quote ID:*\n{quote_id or 'N/A'}"},
                 {"type": "mrkdwn", "text": f"*Filename:*\n{file_name or 'N/A'}"},
                 {"type": "mrkdwn", "text": f"*Amount Paid:*\n{amount_received:.2f} {currency}"},
                 {"type": "mrkdwn", "text": f"*Customer Email:*\n{customer_email or 'N/A'}"},
                 {"type": "mrkdwn", "text": f"*Shipping Name:*\n{customer_name}"}
             ]},
             {"type": "section", "text": {"type": "mrkdwn", "text": f"*Shipping Address:*\n```\n{shipping_address_str}\n```"}},
             {"type": "divider"},
             {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Payment Intent: `{payment_intent_id}` | Received: {received_timestamp}"}]}
        ]
        slack_fallback_text = f"New Order: Quote {quote_id or 'N/A'}, File {file_name or 'N/A'}, Amount {amount_received:.2f} {currency}"

        # --- Get File Path (if available) ---
        file_path_to_upload = None
        # Check if quote_id is valid before lookup
        if quote_id and quote_id not in ['N/A', 'MISSING', None, '']:
            if quote_id in temp_file_storage:
                file_path_to_upload = temp_file_storage.get(quote_id)
                if file_path_to_upload and os.path.exists(file_path_to_upload):
                     logger.info(f"Webhook: Found temp file path '{file_path_to_upload}' for quote '{quote_id}'. Will attempt Slack upload.")
                else:
                     logger.warning(f"Webhook: File path for quote '{quote_id}' found in storage ('{file_path_to_upload}') but file doesn't exist or path is invalid. Proceeding without upload.")
                     file_path_to_upload = None # Reset if file not found
                     # Cleanup the bad entry?
                     cleanup_temp_file_and_storage(quote_id, file_path_to_upload)
            else:
                # Add detailed logging here
                available_keys = list(temp_file_storage.keys())
                logger.error(f"Webhook: Quote ID '{quote_id}' received, but no temporary file path found in storage. Available keys: {available_keys}")
        else:
            logger.error(f"Webhook: No valid Quote ID found in payment intent metadata (received: '{quote_id}'). Cannot look up file for upload.")

        # --- Send Notification (with or without file) ---
        # Use background task to avoid delaying webhook response
        background_tasks.add_task(
            send_slack_notification,
            payload_blocks=slack_blocks,
            fallback_text=slack_fallback_text,
            file_path=file_path_to_upload,
            file_name=file_name,
            quote_id=quote_id
        )

        # NOTE: File path cleanup is now handled *inside* send_slack_notification's finally block

        # TODO: Update order status in DB

    # Handle other events if needed (e.g., payment_intent.payment_failed)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"PaymentIntent failed: {payment_intent.id}. Reason: {payment_intent.get('last_payment_error', {}).get('message')}")
        # Optionally send a different Slack message or log

    else:
        logger.info(f"Unhandled event type: {event['type']}")

    return JSONResponse(content={"received": True})

# --- Run Instruction (for direct execution, though usually run with uvicorn command) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server via __main__ (use 'uvicorn main_api:app --reload' for development)")
    uvicorn.run(app, host="0.0.0.0", port=8000) 