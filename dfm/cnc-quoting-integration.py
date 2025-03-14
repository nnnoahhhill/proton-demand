#!/usr/bin/env python3
"""
CNC Instant Quote Web Application Integration

This module integrates the CNC machining analysis and quoting system
with a web application (e.g., Next.js) through a fast API endpoint.

Features:
- Fast, async processing (< 10 seconds response time)
- Caching of analysis results
- Progressive refinement for complex parts
- STL/STEP file handling
- Result serialization for frontend display
"""

import os
import time
import json
import asyncio
import logging
import base64
import tempfile
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import numpy as np
import trimesh

# Import our CNC analysis modules
from cnc_quoting_system import CNCQuoteAnalyzer
from cnc_feature_extraction import CNCFeatureRecognition

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CNCQuoteAPI')

# Initialize FastAPI app
app = FastAPI(title="CNC Instant Quote API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for analysis results
analysis_cache = {}
quote_cache = {}

# Background task queue
background_tasks = {}

# Response models
class BasicQuoteResponse(BaseModel):
    """Basic quote response (fast initial response)"""
    quote_id: str
    status: str
    basic_price: float
    estimated_time_minutes: float
    lead_time_days: int
    material: str
    is_manufacturable: bool
    confidence: float = 0.8
    message: Optional[str] = None
    bounding_box: Dict[str, float]
    
class DetailedQuoteResponse(BaseModel):
    """Detailed quote with full breakdown"""
    quote_id: str
    status: str
    material: Dict[str, Any]
    machining: Dict[str, Any]
    quality: Dict[str, Any]
    costs: Dict[str, float]
    lead_time_days: int
    manufacturability_score: float
    issues: List[Dict[str, Any]]
    optimization_tips: Optional[List[Dict[str, Any]]] = None
    features: Optional[List[Dict[str, Any]]] = None
    bounding_box: Dict[str, float]
    analysis_time_seconds: float

class QuoteStatusResponse(BaseModel):
    """Quote processing status"""
    quote_id: str
    status: str
    progress: float = 0.0
    message: Optional[str] = None

# Main quote request handler
@app.post("/api/cnc/quote", response_model=Union[BasicQuoteResponse, DetailedQuoteResponse])
async def generate_cnc_quote(
    file: UploadFile = File(...),
    material: str = Form("aluminum_6061"),
    tolerance: str = Form("standard"),
    finish: str = Form("standard"),
    quantity: int = Form(1),
    detailed: bool = Form(False)
):
    """
    Generate a CNC machining quote
    
    Parameters:
    - file: STL or STEP file
    - material: Material type (e.g., aluminum_6061)
    - tolerance: Tolerance class (standard, precision, ultra-precision)
    - finish: Surface finish (standard, fine, mirror)
    - quantity: Number of parts
    - detailed: Return detailed analysis (may take longer)
    
    Returns:
    - Basic or detailed quote response
    """
    # Start timing
    start_time = time.time()
    
    # Save file to temporary location
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
    temp_file_path = temp_file.name
    
    try:
        # Write uploaded file
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Generate a unique quote ID
        quote_id = f"CNC-{int(time.time())}-{hash(temp_file_path) % 10000}"
        
        # Load model
        mesh = trimesh.load_mesh(temp_file_path)
        
        # Create analyzer
        analyzer = CNCQuoteAnalyzer()
        analyzer.mesh = mesh
        analyzer._calculate_basic_stats()
        
        # Get bounding box
        bbox = analyzer.mesh_stats["bounding_box"]
        
        # Perform fast manufacturability check
        is_manufacturable = True  # Simplified check for demo
        
        # Calculate basic cost (quick estimate)
        volumes = analyzer.mesh_stats.get("volume_mm3", 0)
        basic_price = calculate_basic_price(volumes, material, tolerance, finish, quantity)
        
        # Estimate machining time (quick estimate)
        estimated_time_minutes = estimate_basic_machining_time(volumes, material, tolerance, finish)
        
        # Calculate lead time
        lead_time_days = calculate_lead_time(estimated_time_minutes, quantity)
        
        # If we just need a basic quote, return it now
        if not detailed:
            # Start the detailed analysis in the background
            background_tasks[quote_id] = {
                "status": "processing",
                "progress": 0.1,
                "file_path": temp_file_path,
                "params": {
                    "material": material,
                    "tolerance": tolerance, 
                    "finish": finish,
                    "quantity": quantity
                }
            }
            
            # Launch background processing
            asyncio.create_task(process_detailed_quote(quote_id))
            
            # Return basic quote immediately
            basic_response = BasicQuoteResponse(
                quote_id=quote_id,
                status="basic_complete",
                basic_price=basic_price,
                estimated_time_minutes=estimated_time_minutes,
                lead_time_days=lead_time_days,
                material=material,
                is_manufacturable=is_manufacturable,
                confidence=0.8,  # Initial confidence
                message="Basic quote generated. Detailed analysis in progress.",
                bounding_box={
                    "x": bbox["dimensions"]["x"],
                    "y": bbox["dimensions"]["y"],
                    "z": bbox["dimensions"]["z"]
                }
            )
            
            return basic_response
        
        # For detailed request, process the full quote now
        quote = await process_detailed_quote_sync(
            temp_file_path, 
            material, 
            tolerance, 
            finish, 
            quantity
        )
        
        quote["quote_id"] = quote_id
        quote["status"] = "complete"
        quote["analysis_time_seconds"] = time.time() - start_time
        
        # Cache the result
        quote_cache[quote_id] = quote
        
        # Store bounding box
        quote["bounding_box"] = {
            "x": bbox["dimensions"]["x"],
            "y": bbox["dimensions"]["y"],
            "z": bbox["dimensions"]["z"]
        }
        
        return quote
        
    except Exception as e:
        logger.error(f"Error processing quote: {str(e)}")
        return BasicQuoteResponse(
            quote_id=f"ERROR-{int(time.time())}",
            status="error",
            basic_price=0.0,
            estimated_time_minutes=0.0,
            lead_time_days=0,
            material=material,
            is_manufacturable=False,
            confidence=0.0,
            message=f"Error: {str(e)}",
            bounding_box={"x": 0, "y": 0, "z": 0}
        )
    finally:
        # Clean up temporary file if it exists
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

# Get quote status
@app.get("/api/cnc/quote/{quote_id}/status", response_model=QuoteStatusResponse)
async def get_quote_status(quote_id: str):
    """
    Get the status of a processing quote
    
    Parameters:
    - quote_id: Quote ID
    
    Returns:
    - Status information
    """
    # Check if this quote is in the cache
    if quote_id in quote_cache:
        return QuoteStatusResponse(
            quote_id=quote_id,
            status="complete",
            progress=1.0,
            message="Quote is complete"
        )
    
    # Check if it's in progress
    if quote_id in background_tasks:
        task = background_tasks[quote_id]
        return QuoteStatusResponse(
            quote_id=quote_id,
            status=task["status"],
            progress=task["progress"],
            message=task.get("message", "Processing")
        )
    
    # Not found
    return QuoteStatusResponse(
        quote_id=quote_id,
        status="not_found",
        progress=0.0,
        message="Quote not found"
    )

# Get detailed quote
@app.get("/api/cnc/quote/{quote_id}", response_model=DetailedQuoteResponse)
async def get_detailed_quote(quote_id: str):
    """
    Get a detailed quote
    
    Parameters:
    - quote_id: Quote ID
    
    Returns:
    - Detailed quote information
    """
    # Check if this quote is in the cache
    if quote_id in quote_cache:
        return quote_cache[quote_id]
    
    # Check if it's in progress
    if quote_id in background_tasks:
        task = background_tasks[quote_id]
        return DetailedQuoteResponse(
            quote_id=quote_id,
            status="processing",
            material={"name": task["params"]["material"]},
            machining={
                "time_minutes": 0.0,
                "operations": []
            },
            quality={
                "tolerance_class": task["params"]["tolerance"],
                "finish_quality": task["params"]["finish"]
            },
            costs={
                "total": 0.0,
                "