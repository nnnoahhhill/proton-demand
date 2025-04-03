#!/usr/bin/env python3
"""
Manufacturing DFM Analysis API

This is a unified API for Design for Manufacturing (DFM) analysis
supporting multiple manufacturing methods:
- 3D Printing (SLA, FDM, SLS)
- CNC Machining
- Sheet Metal Fabrication (future)

Features:
- Fast analysis of 3D models for manufacturability
- Accurate cost estimation
- Technology recommendation
- Material selection assistance
- Real-time feedback
- Comprehensive reporting

Requirements:
- fastapi
- uvicorn
- pydantic
- python-multipart
- numpy
- trimesh
- pymeshlab (optional for advanced mesh analysis)
"""

import os
import sys
import time
import json
import asyncio
import logging
import tempfile
import importlib.util
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# FastAPI components
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Common utilities
import numpy as np
import trimesh

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ManufacturingDFM-API')

# Constants
API_VERSION = "1.0.0"
ALLOWED_EXTENSIONS = ['.stl', '.stp', '.step', '.STL', '.STP', '.STEP']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Import the DFMAnalyzer for accurate 3D printing analysis
try:
    # Using importlib to handle module names with dashes
    spec = importlib.util.find_spec("dfm.3d_print_dfm_analyzer")
    if spec is not None:
        dfm_analyzer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dfm_analyzer_module)
        DFMAnalyzer = dfm_analyzer_module.DFMAnalyzer
        DEFAULT_CONFIG = dfm_analyzer_module.DEFAULT_CONFIG
        PRINTING_DFM_AVAILABLE = True
    else:
        # Try alternative module name format
        spec = importlib.util.find_spec("dfm.3d-print-dfm-analyzer")
        if spec is not None:
            dfm_analyzer_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dfm_analyzer_module)
            DFMAnalyzer = dfm_analyzer_module.DFMAnalyzer
            DEFAULT_CONFIG = dfm_analyzer_module.DEFAULT_CONFIG
            PRINTING_DFM_AVAILABLE = True
        else:
            logger.warning("3D printing DFM analyzer module not found. Accurate quoting will not be possible.")
            PRINTING_DFM_AVAILABLE = False
except ImportError as e:
    logger.warning(f"3D printing DFM analyzer import error: {str(e)}. Accurate quoting will not be possible.")
    PRINTING_DFM_AVAILABLE = False

# Check if CNC modules are available
try:
    # Try direct imports with sys.path manipulation
    import sys
    import os
    
    # Make sure the dfm directory is in the path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Now try normal imports
    logger.info(f"Attempting to import CNC modules from directory: {current_dir}")
    
    # Import the modules with explicit path due to hyphens in filenames
    import importlib.util
    
    # Load cnc-quoting-system.py
    spec = importlib.util.spec_from_file_location("cnc_quoting_system", 
                                                os.path.join(current_dir, "cnc-quoting-system.py"))
    cnc_quoting_system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cnc_quoting_system)
    
    # Load cnc-feature-extraction.py
    spec = importlib.util.spec_from_file_location("cnc_feature_extraction", 
                                                os.path.join(current_dir, "cnc-feature-extraction.py"))
    cnc_feature_extraction = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cnc_feature_extraction)
    
    # If imports succeeded, get the classes
    CNCQuoteAnalyzer = cnc_quoting_system.CNCQuoteAnalyzer
    CNCFeatureRecognition = cnc_feature_extraction.CNCFeatureRecognition
    MATERIALS = cnc_quoting_system.MATERIALS
    
    logger.info("CNC modules loaded successfully using direct file imports")
    
    # Mark as available
    CNC_DFM_AVAILABLE = True
    logger.info("CNC modules loaded successfully")
    
except ImportError as e:
    CNC_DFM_AVAILABLE = False
    logger.warning(f"CNC modules not available: {str(e)}")
    logger.warning("CNC analysis will be disabled.")
except Exception as e:
    CNC_DFM_AVAILABLE = False
    logger.warning(f"Error loading CNC modules: {str(e)}")
    logger.warning("CNC analysis will be disabled.")

# Enums for manufacturing methods and materials
class ManufacturingMethod(str, Enum):
    THREE_D_PRINTING = "3d_printing"
    CNC_MACHINING = "cnc_machining"
    SHEET_METAL = "sheet_metal"  # Future support
    AUTO_SELECT = "auto_select"  # API will recommend best method

class PrintingTechnology(str, Enum):
    SLA = "sla"  # Stereolithography
    FDM = "fdm"  # Fused Deposition Modeling
    SLS = "sls"  # Selective Laser Sintering

class CNCMachiningType(str, Enum):
    THREE_AXIS = "3_axis"  # 3-axis machining
    FOUR_AXIS = "4_axis"  # 4-axis machining
    FIVE_AXIS = "5_axis"  # 5-axis machining

class ToleranceClass(str, Enum):
    STANDARD = "standard"
    PRECISION = "precision"
    ULTRA_PRECISION = "ultra_precision"

class FinishQuality(str, Enum):
    STANDARD = "standard"
    FINE = "fine"
    MIRROR = "mirror"

# Response Models
class BasicAnalysisResponse(BaseModel):
    """Basic analysis response for quick feedback"""
    analysis_id: str
    status: str
    manufacturing_method: str
    basic_price: float
    estimated_time: float  # in minutes or hours
    lead_time_days: int
    material: str
    is_manufacturable: bool
    confidence: float
    message: Optional[str] = None
    bounding_box: Dict[str, float]

class DetailedAnalysisResponse(BaseModel):
    """Detailed analysis with full breakdown"""
    analysis_id: str
    status: str
    manufacturing_method: str
    material: Dict[str, Any]
    manufacturing: Dict[str, Any]
    quality: Dict[str, Any]
    costs: Dict[str, float]
    lead_time_days: int
    manufacturability_score: float
    issues: List[Dict[str, Any]]
    optimization_tips: Optional[List[Dict[str, Any]]] = None
    features: Optional[List[Dict[str, Any]]] = None
    bounding_box: Dict[str, float]
    analysis_time_seconds: float

class AnalysisStatusResponse(BaseModel):
    """Analysis processing status"""
    analysis_id: str
    status: str
    progress: float = 0.0
    message: Optional[str] = None

class TechRecommendationResponse(BaseModel):
    """Technology recommendation response"""
    best_method: str
    confidence: float
    alternatives: List[Dict[str, Any]]
    explanation: str

# Add new response models for the getQuote endpoint
class DFMIssue(BaseModel):
    """Detailed DFM issue information"""
    type: str
    severity: str
    description: str
    location: Optional[Dict[str, float]] = None

class ManufacturingDetails(BaseModel):
    """Detailed manufacturing information from DFM analysis"""
    process: str
    material: str
    finish: str
    boundingBox: Dict[str, float]
    volume: float
    surfaceArea: float
    printabilityScore: Optional[float] = None
    estimatedPrintTime: Optional[str] = None
    materialUsage: Optional[float] = None
    materialCost: Optional[float] = None
    supportRequirements: Optional[str] = None

class QuoteResponse(BaseModel):
    """Quote response with manufacturing details and DFM results"""
    success: bool
    quote_id: str
    price: Optional[float] = None
    currency: str = "USD"
    lead_time_days: Optional[int] = None
    manufacturing_details: Optional[ManufacturingDetails] = None
    dfm_issues: Optional[List[DFMIssue]] = None
    message: Optional[str] = None
    error: Optional[str] = None

# In-memory cache for analysis results
analysis_cache = {}
background_tasks = {}

# Initialize FastAPI app
app = FastAPI(
    title="Manufacturing DFM Analysis API",
    description="Design for Manufacturing analysis for 3D printing and CNC machining",
    version=API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Access-Control-Allow-Origin"],
)

# Helper function to validate uploaded files
def validate_model_file(file: UploadFile) -> bool:
    """Validate the uploaded model file
    
    Args:
        file: The uploaded file
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file extension: {ext}")
        return False
        
    # Check file size (TODO: implement proper size checking)
    # This would require reading the file content which we'll do later
    
    return True

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Manufacturing DFM Analysis API",
        "version": API_VERSION,
        "status": "operational",
        "supported_methods": [
            "3D Printing" if PRINTING_DFM_AVAILABLE else None,
            "CNC Machining" if CNC_DFM_AVAILABLE else None
        ],
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "manufacturing-dfm-api",
        "version": API_VERSION,
        "time": datetime.now().isoformat()
    }

@app.post("/api/analyze", response_model=Union[BasicAnalysisResponse, DetailedAnalysisResponse])
async def analyze_model(
    file: UploadFile = File(...),
    manufacturing_method: ManufacturingMethod = Form(ManufacturingMethod.AUTO_SELECT),
    material: str = Form(None),
    tolerance: ToleranceClass = Form(ToleranceClass.STANDARD),
    finish: FinishQuality = Form(FinishQuality.STANDARD),
    quantity: int = Form(1),
    detailed: bool = Form(False)
):
    """
    Analyze a 3D model for manufacturability and generate cost estimate
    
    Args:
        file: STL or STEP file
        manufacturing_method: Manufacturing method to analyze for
        material: Material ID (if not specified, a default will be used)
        tolerance: Tolerance class
        finish: Surface finish quality
        quantity: Number of parts
        detailed: Return detailed analysis (may take longer)
        
    Returns:
        Basic or detailed analysis response
    """
    # Start timing
    start_time = time.time()
    
    # Validate the file
    if not validate_model_file(file):
        raise HTTPException(status_code=400, detail="Invalid file format. Supported formats: STL, STEP")
    
    # Save file to temporary location
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
    temp_file_path = temp_file.name
    
    try:
        # Write uploaded file
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Generate a unique analysis ID
        analysis_id = f"DFM-{int(time.time())}-{hash(temp_file_path) % 10000}"
        
        # Determine which analysis method to use
        if manufacturing_method == ManufacturingMethod.AUTO_SELECT:
            # Auto-select based on file attributes
            manufacturing_method = select_manufacturing_method(temp_file_path)
        
        # Load model with trimesh for basic analysis
        try:
            mesh = trimesh.load_mesh(temp_file_path)
            bounds = mesh.bounds if hasattr(mesh, 'bounds') else None
            if bounds is not None:
                dimensions = bounds[1] - bounds[0]
                bbox = {
                    "x": float(dimensions[0]),
                    "y": float(dimensions[1]),
                    "z": float(dimensions[2])
                }
            else:
                bbox = {"x": 0, "y": 0, "z": 0}
                
            volume = float(mesh.volume) if hasattr(mesh, 'volume') and mesh.volume is not None else 0
                
        except Exception as e:
            logger.error(f"Error loading mesh: {str(e)}")
            bbox = {"x": 0, "y": 0, "z": 0}
            volume = 0
        
        # Determine which specific analysis to perform
        if manufacturing_method == ManufacturingMethod.THREE_D_PRINTING:
            if not PRINTING_DFM_AVAILABLE:
                raise HTTPException(status_code=503, detail="3D printing analysis is not available")
                
            # If material is not specified, use a default based on printing technology
            if not material:
                material = "Resin"  # Default for SLA
                
            # For now, return a placeholder response
            # TODO: Implement actual 3D printing analysis
            basic_response = BasicAnalysisResponse(
                analysis_id=analysis_id,
                status="basic_complete",
                manufacturing_method="3d_printing",
                basic_price=estimate_3d_printing_price(volume, material),
                estimated_time=estimate_3d_printing_time(volume, material),
                lead_time_days=estimate_lead_time(volume, quantity),
                material=material,
                is_manufacturable=True,  # Simplified for now
                confidence=0.8,
                message="Basic analysis complete. Detailed analysis will be performed in the background.",
                bounding_box=bbox
            )
            
            # Start detailed analysis in background if requested
            if detailed:
                background_tasks[analysis_id] = {
                    "status": "processing",
                    "progress": 0.1,
                    "file_path": temp_file_path,
                    "params": {
                        "manufacturing_method": manufacturing_method,
                        "material": material,
                        "tolerance": tolerance, 
                        "finish": finish,
                        "quantity": quantity
                    }
                }
                
                # Launch background processing
                asyncio.create_task(process_detailed_analysis(analysis_id))
            
            return basic_response
            
        elif manufacturing_method == ManufacturingMethod.CNC_MACHINING:
            if not CNC_DFM_AVAILABLE:
                raise HTTPException(status_code=503, detail="CNC machining analysis is not available")
                
            # If material is not specified, use aluminum as default
            if not material:
                material = "aluminum_6061"
                
            # For now, use the existing CNC analysis system if available
            try:
                # CNCQuoteAnalyzer should already be available from global imports
                # If not, this will raise a NameError caught by the outer try/except
                
                # Create analyzer
                analyzer = CNCQuoteAnalyzer()
                analyzer.mesh = mesh
                analyzer._calculate_basic_stats()
                
                # Basic estimate
                basic_price = estimate_cnc_price(volume, material, tolerance, finish, quantity)
                estimated_time = estimate_cnc_time(volume, material, tolerance, finish)
                lead_time_days = estimate_lead_time(estimated_time, quantity)
                
                basic_response = BasicAnalysisResponse(
                    analysis_id=analysis_id,
                    status="basic_complete",
                    manufacturing_method="cnc_machining",
                    basic_price=basic_price,
                    estimated_time=estimated_time,
                    lead_time_days=lead_time_days,
                    material=material,
                    is_manufacturable=True,  # Simplified for now
                    confidence=0.8,
                    message="Basic CNC analysis complete.",
                    bounding_box=bbox
                )
                
                # Start detailed analysis in background if requested
                if detailed:
                    background_tasks[analysis_id] = {
                        "status": "processing",
                        "progress": 0.1,
                        "file_path": temp_file_path,
                        "params": {
                            "manufacturing_method": manufacturing_method,
                            "material": material,
                            "tolerance": tolerance, 
                            "finish": finish,
                            "quantity": quantity
                        }
                    }
                    
                    # Launch background processing
                    asyncio.create_task(process_detailed_analysis(analysis_id))
                
                return basic_response
                
            except Exception as e:
                logger.error(f"Error in CNC analysis: {str(e)}")
                raise HTTPException(status_code=500, detail=f"CNC analysis error: {str(e)}")
        
        else:
            # Unsupported manufacturing method
            raise HTTPException(status_code=400, detail=f"Unsupported manufacturing method: {manufacturing_method}")
            
    except Exception as e:
        logger.error(f"Error processing analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    finally:
        # Clean up temporary file if it exists
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@app.get("/api/analyze/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """
    Get the status of an analysis
    
    Args:
        analysis_id: Analysis ID
        
    Returns:
        Status information
    """
    # Check if this analysis is in the cache
    if analysis_id in analysis_cache:
        return AnalysisStatusResponse(
            analysis_id=analysis_id,
            status="complete",
            progress=1.0,
            message="Analysis is complete"
        )
    
    # Check if it's in progress
    if analysis_id in background_tasks:
        task = background_tasks[analysis_id]
        return AnalysisStatusResponse(
            analysis_id=analysis_id,
            status=task["status"],
            progress=task["progress"],
            message=task.get("message", "Processing")
        )
    
    # Not found
    raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

@app.get("/api/analyze/{analysis_id}", response_model=DetailedAnalysisResponse)
async def get_detailed_analysis(analysis_id: str):
    """
    Get detailed analysis results
    
    Args:
        analysis_id: Analysis ID
        
    Returns:
        Detailed analysis information
    """
    # Check if this analysis is in the cache
    if analysis_id in analysis_cache:
        return analysis_cache[analysis_id]
    
    # Check if it's in progress
    if analysis_id in background_tasks:
        task = background_tasks[analysis_id]
        raise HTTPException(status_code=202, 
                           detail=f"Analysis in progress ({task['progress']:.0%} complete)")
    
    # Not found
    raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

@app.get("/api/recommend", response_model=TechRecommendationResponse)
async def recommend_technology(
    file: UploadFile = File(...),
    max_budget: Optional[float] = None,
    min_resolution: Optional[float] = None,
    max_lead_time: Optional[int] = None
):
    """
    Recommend the best manufacturing technology for a model
    
    Args:
        file: STL or STEP file
        max_budget: Maximum budget constraint
        min_resolution: Minimum resolution required (mm)
        max_lead_time: Maximum acceptable lead time (days)
        
    Returns:
        Technology recommendation
    """
    # TODO: Implement technology recommendation logic
    
    # For now return a placeholder
    return TechRecommendationResponse(
        best_method="3d_printing",
        confidence=0.8,
        alternatives=[
            {"method": "cnc_machining", "confidence": 0.6, "price": 250.0, "lead_time": 5}
        ],
        explanation="Based on the model geometry, 3D printing is recommended for better cost efficiency."
    )

@app.get("/api/materials")
async def get_materials(manufacturing_method: ManufacturingMethod):
    """
    Get available materials for a manufacturing method
    
    Args:
        manufacturing_method: Manufacturing method
        
    Returns:
        List of available materials with properties
    """
    # Define helper function for module loading
    def load_module_by_path(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return None
    if manufacturing_method == ManufacturingMethod.THREE_D_PRINTING:
        # Return 3D printing materials
        return {
            "materials": [
                {
                    "id": "resin_standard",
                    "name": "Standard Resin",
                    "type": "SLA",
                    "color": "Clear",
                    "cost_per_cm3": 0.30
                },
                {
                    "id": "resin_tough",
                    "name": "Tough Resin",
                    "type": "SLA",
                    "color": "Gray",
                    "cost_per_cm3": 0.35
                },
                {
                    "id": "pla",
                    "name": "PLA",
                    "type": "FDM",
                    "color": "White",
                    "cost_per_cm3": 0.15
                },
                {
                    "id": "abs",
                    "name": "ABS",
                    "type": "FDM",
                    "color": "White",
                    "cost_per_cm3": 0.18
                },
                {
                    "id": "nylon_pa12",
                    "name": "Nylon (PA12)",
                    "type": "SLS",
                    "color": "White",
                    "cost_per_cm3": 0.40
                }
            ]
        }
    elif manufacturing_method == ManufacturingMethod.CNC_MACHINING:
        # Return CNC machining materials
        try:
            # MATERIALS should already be available from global imports
            # If not, this will raise a NameError caught by the outer try/except
            
            materials = []
            for material_id, material in MATERIALS.items():
                materials.append({
                    "id": material_id,
                    "name": material.name,
                    "type": material.type,
                    "density": material.density,
                    "cost_per_kg": material.cost_per_kg,
                    "machinability": material.machinability
                })
                
            return {"materials": materials}
        except ImportError:
            # Fallback if CNC module not available
            return {
                "materials": [
                    {
                        "id": "aluminum_6061",
                        "name": "Aluminum 6061-T6",
                        "type": "metal",
                        "density": 2.7,
                        "cost_per_kg": 15.0,
                        "machinability": 1.0
                    },
                    {
                        "id": "steel_1018",
                        "name": "Steel 1018",
                        "type": "metal",
                        "density": 7.87,
                        "cost_per_kg": 12.0,
                        "machinability": 1.5
                    }
                ]
            }
    else:
        # Unsupported manufacturing method
        raise HTTPException(status_code=400, 
                           detail=f"Unsupported manufacturing method: {manufacturing_method}")

# Helper Functions
def select_manufacturing_method(file_path):
    """
    Auto-select the best manufacturing method for a model
    
    Args:
        file_path: Path to the model file
        
    Returns:
        ManufacturingMethod: Selected manufacturing method
    """
    # TODO: Implement auto-selection logic based on geometry analysis
    
    # For now, choose based on file extension
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.stl', '.STL']:
        # STL files are commonly used for 3D printing
        return ManufacturingMethod.THREE_D_PRINTING
    elif ext in ['.step', '.stp', '.STEP', '.STP']:
        # STEP files are commonly used for CNC machining
        return ManufacturingMethod.CNC_MACHINING
    else:
        # Default to 3D printing
        return ManufacturingMethod.THREE_D_PRINTING

def estimate_3d_printing_price(volume_mm3, material):
    """
    Generate a quick estimate for 3D printing cost
    
    Args:
        volume_mm3: Model volume in mm³
        material: Material type
        
    Returns:
        float: Estimated price
    """
    # Convert to cm³
    volume_cm3 = volume_mm3 / 1000.0
    
    # Base rates per cm³ for different materials
    material_rates = {
        "Resin": 0.30,      # Standard resin
        "ToughResin": 0.35, # Tough resin
        "PLA": 0.15,        # PLA
        "ABS": 0.18,        # ABS
        "PETG": 0.20,       # PETG
        "Nylon": 0.40       # Nylon (SLS)
    }
    
    # Get base rate, default to resin if material not found
    base_rate = material_rates.get(material, 0.30)
    
    # Calculate material cost
    material_cost = volume_cm3 * base_rate
    
    # Add setup cost
    setup_cost = 15.0
    
    # Add handling fee
    handling_fee = 5.0
    
    # Total cost
    total_cost = material_cost + setup_cost + handling_fee
    
    # Minimum cost
    return max(total_cost, 25.0)

def estimate_3d_printing_time(volume_mm3, material):
    """
    Estimate 3D printing time in minutes
    
    Args:
        volume_mm3: Model volume in mm³
        material: Material type
        
    Returns:
        float: Estimated print time in minutes
    """
    # Convert to cm³
    volume_cm3 = volume_mm3 / 1000.0
    
    # Base print speed factors (cm³ per hour)
    material_speed = {
        "Resin": 15.0,     # SLA resin
        "ToughResin": 12.0, # Tough resin
        "PLA": 20.0,       # PLA
        "ABS": 18.0,       # ABS
        "PETG": 19.0,      # PETG
        "Nylon": 10.0      # Nylon (SLS)
    }
    
    # Get speed factor, default to resin if material not found
    speed = material_speed.get(material, 15.0)
    
    # Calculate print time in hours
    print_time_hours = volume_cm3 / speed
    
    # Convert to minutes
    print_time_minutes = print_time_hours * 60.0
    
    # Add setup time
    setup_time = 30.0
    
    # Total time
    total_time = print_time_minutes + setup_time
    
    return total_time

def estimate_cnc_price(volume_mm3, material, tolerance, finish, quantity):
    """
    Generate a quick estimate for CNC machining cost
    
    Args:
        volume_mm3: Model volume in mm³
        material: Material type
        tolerance: Tolerance class
        finish: Surface finish
        quantity: Quantity
        
    Returns:
        float: Estimated price
    """
    # Convert to cm³
    volume_cm3 = volume_mm3 / 1000.0
    
    # Base rates per cm³ for different materials
    material_rates = {
        "aluminum_6061": 2.5,
        "aluminum_7075": 3.5,
        "stainless_304": 5.0,
        "brass_360": 4.0,
        "steel_1018": 3.0,
        "titanium_6al4v": 12.0,
        "plastic_delrin": 2.0,
        "plastic_hdpe": 1.5
    }
    
    # Get base rate, default to aluminum if material not found
    base_rate = material_rates.get(material, 2.5)
    
    # Apply tolerance and finish multipliers
    tolerance_multipliers = {
        "standard": 1.0,
        "precision": 1.3,
        "ultra_precision": 1.8
    }
    
    finish_multipliers = {
        "standard": 1.0,
        "fine": 1.2,
        "mirror": 1.5
    }
    
    tolerance_factor = tolerance_multipliers.get(str(tolerance), 1.0)
    finish_factor = finish_multipliers.get(str(finish), 1.0)
    
    # Calculate base price
    base_price = volume_cm3 * base_rate * tolerance_factor * finish_factor
    
    # Add setup cost
    setup_cost = 50.0
    
    # Apply quantity discount
    if quantity <= 1:
        quantity_factor = 1.0
    elif quantity <= 5:
        quantity_factor = 0.9
    elif quantity <= 10:
        quantity_factor = 0.85
    else:
        quantity_factor = 0.8
        
    # Calculate final price
    price_per_unit = base_price * quantity_factor
    total_price = (price_per_unit * quantity) + setup_cost
    
    return total_price

def estimate_cnc_time(volume_mm3, material, tolerance, finish):
    """
    Estimate CNC machining time in minutes
    
    Args:
        volume_mm3: Model volume in mm³
        material: Material type
        tolerance: Tolerance class
        finish: Surface finish
        
    Returns:
        float: Estimated machining time in minutes
    """
    # Convert to cm³
    volume_cm3 = volume_mm3 / 1000.0
    
    # Base time factors (minutes per cm³)
    material_time_factors = {
        "aluminum_6061": 5.0,
        "aluminum_7075": 5.5,
        "stainless_304": 10.0,
        "brass_360": 4.0,
        "steel_1018": 7.5,
        "titanium_6al4v": 15.0,
        "plastic_delrin": 3.0,
        "plastic_hdpe": 2.0
    }
    
    # Get base time factor, default to aluminum if not found
    base_factor = material_time_factors.get(material, 5.0)
    
    # Apply modifiers for tolerance and finish
    tolerance_time_factors = {
        "standard": 1.0,
        "precision": 1.5,
        "ultra_precision": 2.5
    }
    
    finish_time_factors = {
        "standard": 1.0,
        "fine": 1.3,
        "mirror": 2.0
    }
    
    tolerance_factor = tolerance_time_factors.get(str(tolerance), 1.0)
    finish_factor = finish_time_factors.get(str(finish), 1.0)
    
    # Estimate machining time
    base_time = volume_cm3 * base_factor
    adjusted_time = base_time * tolerance_factor * finish_factor
    
    # Add setup time
    setup_time = 30.0  # 30 minutes
    
    # Total time
    total_time = adjusted_time + setup_time
    
    return total_time

def estimate_lead_time(processing_time_minutes, quantity):
    """
    Estimate lead time in business days
    
    Args:
        processing_time_minutes: Processing time in minutes
        quantity: Quantity
        
    Returns:
        int: Estimated lead time in business days
    """
    # Convert to hours
    processing_hours = processing_time_minutes / 60.0
    
    # Calculate total hours for all parts
    total_hours = processing_hours * quantity
    
    # Basic lead time calculation
    if total_hours < 2:
        return 2  # 2 days for small parts
    elif total_hours < 8:
        return 3  # 3 days for medium parts
    elif total_hours < 24:
        return 5  # 5 days
    else:
        # For longer processing, scale with time
        return int(5 + total_hours / 16)  # Add 1 day per 16 hours

async def process_detailed_analysis(analysis_id):
    """
    Process detailed analysis in the background
    
    Args:
        analysis_id: The analysis ID to process
    """
    task_info = background_tasks.get(analysis_id)
    if not task_info:
        return
        
    try:
        # Extract parameters
        file_path = task_info["file_path"]
        manufacturing_method = task_info["params"]["manufacturing_method"]
        material = task_info["params"]["material"]
        tolerance = task_info["params"]["tolerance"]
        finish = task_info["params"]["finish"]
        quantity = task_info["params"]["quantity"]
        
        # Update status
        task_info["status"] = "processing"
        task_info["progress"] = 0.2
        task_info["message"] = "Loading and analyzing model..."
        
        # Process based on manufacturing method
        if manufacturing_method == ManufacturingMethod.THREE_D_PRINTING:
            # TODO: Implement 3D printing detailed analysis
            # For now, return a placeholder
            
            # Update status
            task_info["status"] = "complete"
            task_info["progress"] = 1.0
            task_info["message"] = "Analysis complete"
            
            # Add result to cache (placeholder for now)
            analysis_cache[analysis_id] = {
                "analysis_id": analysis_id,
                "status": "complete",
                "manufacturing_method": "3d_printing",
                "material": {
                    "name": material,
                    "type": "resin",
                    "cost": 0.0
                },
                "manufacturing": {
                    "time_minutes": 0.0,
                    "operations": []
                },
                "quality": {
                    "tolerance_class": tolerance,
                    "finish_quality": finish
                },
                "costs": {
                    "material": 0.0,
                    "processing": 0.0,
                    "setup": 0.0,
                    "total": 0.0
                },
                "lead_time_days": 0,
                "manufacturability_score": 0.0,
                "issues": [],
                "bounding_box": {"x": 0, "y": 0, "z": 0},
                "analysis_time_seconds": 0.0
            }
        
        elif manufacturing_method == ManufacturingMethod.CNC_MACHINING:
            # Process the CNC analysis if available
            if CNC_DFM_AVAILABLE:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: process_cnc_analysis(
                        file_path, material, tolerance, finish, quantity
                    )
                )
                
                # Update status
                task_info["status"] = "complete"
                task_info["progress"] = 1.0
                task_info["message"] = "Analysis complete"
                
                # Add to cache
                result["analysis_id"] = analysis_id
                result["status"] = "complete"
                analysis_cache[analysis_id] = result
            else:
                task_info["status"] = "error"
                task_info["progress"] = 0.0
                task_info["message"] = "CNC analysis not available"
        
        else:
            # Unsupported method
            task_info["status"] = "error"
            task_info["progress"] = 0.0
            task_info["message"] = f"Unsupported manufacturing method: {manufacturing_method}"
            
    except Exception as e:
        logger.error(f"Error in background processing for {analysis_id}: {str(e)}")
        task_info["status"] = "error"
        task_info["progress"] = 0.0
        task_info["message"] = f"Error: {str(e)}"
    finally:
        # Clean up temporary file if it exists
        if "file_path" in task_info and os.path.exists(task_info["file_path"]):
            try:
                os.unlink(task_info["file_path"])
            except:
                pass

def process_cnc_analysis(file_path, material, tolerance, finish, quantity):
    """
    Process CNC analysis (runs in a separate thread)
    
    Args:
        file_path: Path to the model file
        material: Material identifier
        tolerance: Tolerance class
        finish: Surface finish
        quantity: Quantity
        
    Returns:
        dict: Analysis results
    """
    try:
        # CNCQuoteAnalyzer should already be available from global imports
        # If not, this will raise a NameError caught by the try/except
        
        # Create analyzer
        analyzer = CNCQuoteAnalyzer()
        
        # Load model
        analyzer.load_model(file_path)
        
        # Generate detailed quote
        quote = analyzer.generate_quote(material, tolerance, finish)
        
        # Adjust for quantity if necessary
        if quantity > 1:
            # This should be handled in the CNC quoting system
            pass
            
        return quote
        
    except Exception as e:
        logger.error(f"Error in CNC analysis: {str(e)}")
        return {
            "status": "error",
            "message": f"Error in CNC analysis: {str(e)}",
            "manufacturing_method": "cnc_machining",
            "material": {"name": material},
            "costs": {"total": 0.0},
            "lead_time_days": 0,
            "manufacturability_score": 0.0,
            "issues": [{"type": "error", "message": str(e)}],
            "bounding_box": {"x": 0, "y": 0, "z": 0},
            "analysis_time_seconds": 0.0
        }

@app.post("/api/getQuote", response_model=QuoteResponse)
async def get_quote(
    model_file: UploadFile = File(..., description="3D model file (.stl, .step, or .stp)"),
    process: str = Form(..., description="Manufacturing process (CNC, 3DP_SLA, 3DP_SLS, 3DP_FDM, SHEET_METAL)"),
    material: str = Form(..., description="Material to use, specific to the selected process"),
    finish: str = Form(..., description="Surface finish quality, specific to the selected process"),
    drawing_file: Optional[UploadFile] = File(None, description="Optional engineering drawing (.pdf)")
):
    """
    Get a manufacturing quote with DFM analysis in a single call
    
    This endpoint performs Design for Manufacturing analysis and returns a quote
    if the part can be manufactured. If DFM issues are found, they will be returned
    in the response.
    
    Args:
        model_file: 3D model file (.stl, .step, or .stp)
        process: Manufacturing process (CNC, 3DP_SLA, 3DP_SLS, 3DP_FDM, SHEET_METAL)
        material: Material to use, specific to the selected process
        finish: Surface finish quality, specific to the selected process
        drawing_file: Optional engineering drawing (.pdf)
        
    Returns:
        Quote with pricing, lead time and manufacturing details if DFM passes,
        or DFM issues if the part cannot be manufactured.
    """
    # Start timing
    start_time = time.time()
    
    # Generate a unique quote ID
    quote_id = f"QUOTE-{int(time.time())}-{abs(hash(model_file.filename) % 10000)}"
    
    # Map process to ManufacturingMethod enum
    manufacturing_method_map = {
        "CNC": ManufacturingMethod.CNC_MACHINING,
        "3DP_SLA": ManufacturingMethod.THREE_D_PRINTING,
        "3DP_SLS": ManufacturingMethod.THREE_D_PRINTING,
        "3DP_FDM": ManufacturingMethod.THREE_D_PRINTING,
        "SHEET_METAL": ManufacturingMethod.SHEET_METAL
    }
    
    # Map to PrintingTechnology for 3D printing processes
    printing_technology = None
    if process.startswith("3DP_"):
        process_tech_map = {
            "3DP_SLA": PrintingTechnology.SLA,
            "3DP_SLS": PrintingTechnology.SLS,
            "3DP_FDM": PrintingTechnology.FDM
        }
        printing_technology = process_tech_map.get(process)
    
    try:
        # Validate the process
        if process not in manufacturing_method_map:
            return QuoteResponse(
                success=False,
                quote_id=quote_id,
                error=f"Invalid process. Must be one of: {', '.join(manufacturing_method_map.keys())}"
            )
        
        manufacturing_method = manufacturing_method_map[process]
        
        # Validate the model file
        if not validate_model_file(model_file):
            return QuoteResponse(
                success=False,
                quote_id=quote_id,
                error="Invalid model file format. Supported formats: STL, STEP"
            )
        
        # Validate drawing file if provided
        if drawing_file and not drawing_file.filename.lower().endswith('.pdf'):
            return QuoteResponse(
                success=False,
                quote_id=quote_id,
                error="Invalid drawing file format. Only PDF is supported."
            )
        
        # Save model file to temporary location
        model_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(model_file.filename)[1])
        model_file_path = model_temp_file.name
        
        # Save drawing file if provided
        drawing_file_path = None
        if drawing_file:
            drawing_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            drawing_file_path = drawing_temp_file.name
            drawing_content = await drawing_file.read()
            drawing_temp_file.write(drawing_content)
            drawing_temp_file.close()
        
        # Write uploaded model file
        model_content = await model_file.read()
        model_temp_file.write(model_content)
        model_temp_file.close()
        
        # Calculate manufacturing details and perform DFM analysis
        if manufacturing_method == ManufacturingMethod.THREE_D_PRINTING:
            if not PRINTING_DFM_AVAILABLE:
                return QuoteResponse(
                    success=False,
                    quote_id=quote_id,
                    error="3D printing analysis is not available. Please ensure DFMAnalyzer is properly installed."
                )
            
            # Perform 3D printing DFM analysis using the enhanced function
            printing_analysis_result = analyze_3d_printing(
                model_file_path, 
                material, 
                printing_technology, 
                finish
            )
            
            # Check if part is manufacturable
            if not printing_analysis_result["is_manufacturable"]:
                return QuoteResponse(
                    success=False,
                    quote_id=quote_id,
                    message="Part cannot be manufactured due to DFM issues",
                    dfm_issues=[
                        DFMIssue(
                            type=issue["type"],
                            severity=issue["severity"],
                            description=issue["description"],
                            location=issue.get("location")
                        )
                        for issue in printing_analysis_result["issues"]
                    ]
                )
            
            # Get detailed manufacturing info from analysis
            bbox = {}
            if "bounding_box" in printing_analysis_result:
                # Convert from width/depth/height to x/y/z format
                bbox = {
                    "x": printing_analysis_result["bounding_box"].get("width", 0),
                    "y": printing_analysis_result["bounding_box"].get("depth", 0),
                    "z": printing_analysis_result["bounding_box"].get("height", 0)
                }
            else:
                # Fallback to loading mesh with trimesh
                try:
                    mesh = trimesh.load_mesh(model_file_path)
                    bounds = mesh.bounds if hasattr(mesh, 'bounds') else None
                    if bounds is not None:
                        dimensions = bounds[1] - bounds[0]
                        bbox = {
                            "x": float(dimensions[0]),
                            "y": float(dimensions[1]),
                            "z": float(dimensions[2])
                        }
                    else:
                        bbox = {"x": 0, "y": 0, "z": 0}
                except Exception as e:
                    logger.error(f"Error loading mesh: {str(e)}")
                    bbox = {"x": 0, "y": 0, "z": 0}
            
            # Get volume and surface area
            volume = printing_analysis_result.get("volume_mm3", 0)
            surface_area = printing_analysis_result.get("surface_area_mm2", 0)
            
            # Get price and lead time
            price = printing_analysis_result["basic_price"]
            lead_time_days = printing_analysis_result["lead_time_days"]
            
            # Return detailed quote with all the available information
            return QuoteResponse(
                success=True,
                quote_id=quote_id,
                price=price,
                currency="USD",
                lead_time_days=lead_time_days,
                manufacturing_details=ManufacturingDetails(
                    process=process,
                    material=material,
                    finish=finish,
                    boundingBox=bbox,
                    volume=volume,
                    surfaceArea=surface_area,
                    printabilityScore=printing_analysis_result.get("printability_score", 1.0),
                    estimatedPrintTime=printing_analysis_result.get("estimated_print_time", "N/A"),
                    materialUsage=printing_analysis_result.get("material_usage_g", 0.0),
                    materialCost=printing_analysis_result.get("material_cost", 0.0),
                    supportRequirements=printing_analysis_result.get("support_volume_estimate", "N/A")
                )
            )
        
        # Continue with other manufacturing methods unchanged
        elif manufacturing_method == ManufacturingMethod.CNC_MACHINING:
            # Existing CNC implementation code remains unchanged
            if not CNC_DFM_AVAILABLE:
                return QuoteResponse(
                    success=False,
                    quote_id=quote_id,
                    error="CNC machining analysis is not available"
                )
            
            # Perform CNC machining DFM analysis
            try:
                # Use CNCQuoteAnalyzer
                analyzer = CNCQuoteAnalyzer()
                analyzer.load_model(model_file_path)
                analysis_result = analyzer.analyze_model(material=material, finish=finish)
                
                # Check if part is manufacturable
                if not analysis_result["is_manufacturable"]:
                    return QuoteResponse(
                        success=False,
                        quote_id=quote_id,
                        message="Part cannot be manufactured due to DFM issues",
                        dfm_issues=[
                            DFMIssue(
                                type=issue["type"],
                                severity=issue["severity"],
                                description=issue["description"],
                                location=issue.get("location")
                            )
                            for issue in analysis_result["issues"]
                        ]
                    )
                
                # Calculate price and lead time
                price = analysis_result["costs"]["total"] if "costs" in analysis_result else analysis_result.get("basic_price", 0)
                lead_time_days = analysis_result.get("lead_time_days", 7)
                
                # Load mesh for basic dimensions if not provided by analyzer
                try:
                    mesh = trimesh.load_mesh(model_file_path)
                    bounds = mesh.bounds if hasattr(mesh, 'bounds') else None
                    if bounds is not None:
                        dimensions = bounds[1] - bounds[0]
                        bbox = {
                            "x": float(dimensions[0]),
                            "y": float(dimensions[1]),
                            "z": float(dimensions[2])
                        }
                    else:
                        bbox = {"x": 0, "y": 0, "z": 0}
                    volume = float(mesh.volume) if hasattr(mesh, 'volume') and mesh.volume is not None else 0
                    surface_area = float(mesh.area) if hasattr(mesh, 'area') and mesh.area is not None else 0
                except Exception as e:
                    logger.error(f"Error loading mesh: {str(e)}")
                    bbox = {"x": 0, "y": 0, "z": 0}
                    volume = 0
                    surface_area = 0
                
                # Return successful quote
                return QuoteResponse(
                    success=True,
                    quote_id=quote_id,
                    price=price,
                    currency="USD",
                    lead_time_days=lead_time_days,
                    manufacturing_details=ManufacturingDetails(
                        process=process,
                        material=material,
                        finish=finish,
                        boundingBox=bbox,
                        volume=volume,
                        surfaceArea=surface_area
                    )
                )
            
            except Exception as e:
                logger.error(f"Error in CNC analysis: {str(e)}")
                return QuoteResponse(
                    success=False,
                    quote_id=quote_id,
                    error=f"Error in CNC analysis: {str(e)}"
                )
                
        elif manufacturing_method == ManufacturingMethod.SHEET_METAL:
            # TODO: Implement sheet metal analysis when available
            return QuoteResponse(
                success=False,
                quote_id=quote_id,
                error="Sheet metal analysis is not fully implemented yet"
            )
        
        else:
            return QuoteResponse(
                success=False,
                quote_id=quote_id,
                error=f"Unsupported manufacturing method: {process}"
            )
            
    except Exception as e:
        logger.error(f"Error processing quote request: {str(e)}")
        return QuoteResponse(
            success=False,
            quote_id=quote_id,
            error=f"Error processing quote request: {str(e)}"
        )
    finally:
        # Calculate execution time
        execution_time = time.time() - start_time
        logger.info(f"getQuote request processed in {execution_time:.2f} seconds")
        
        # Clean up temporary files
        try:
            if 'model_file_path' in locals() and os.path.exists(model_file_path):
                os.unlink(model_file_path)
            if 'drawing_file_path' in locals() and drawing_file_path and os.path.exists(drawing_file_path):
                os.unlink(drawing_file_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

# Define helper function for 3D printing analysis
def analyze_3d_printing(model_path, material, technology, finish):
    """
    Perform 3D printing DFM analysis using the specialized DFMAnalyzer
    
    Args:
        model_path: Path to the model file
        material: Material to use
        technology: PrintingTechnology enum value
        finish: Surface finish quality
        
    Returns:
        Dictionary with analysis results
    """
    if not PRINTING_DFM_AVAILABLE:
        raise RuntimeError("3D printing DFM analyzer not available. Cannot perform accurate analysis.")
    
    try:
        # Map technology to printer type for DFMAnalyzer
        printer_type_map = {
            PrintingTechnology.SLA: "SLA",
            PrintingTechnology.SLS: "SLS",
            PrintingTechnology.FDM: "FDM"
        }
        printer_type = printer_type_map.get(technology, "SLA")
        
        # Map material to appropriate type
        material_type_map = {
            "resin_standard": "Resin",
            "nylon_12_white": "Nylon",
            "nylon_12_black": "Nylon",
            "pla": "PLA",
            "abs": "ABS",
            "petg": "PETG",
            "tpu": "Flexible"
        }
        material_type = material_type_map.get(material, "Resin")
        
        # Map finish to layer height
        layer_height_map = {
            "standard": 0.1,  # Standard quality
            "fine": 0.05      # Fine quality
        }
        layer_height = layer_height_map.get(finish.lower(), 0.1)
        
        # Configure DFMAnalyzer
        config = DEFAULT_CONFIG.copy()
        config["printer_type"] = printer_type
        config["material_type"] = material_type
        config["layer_height"] = layer_height
        config["use_external_slicer"] = True
        
        # Create analyzer and run analysis
        analyzer = DFMAnalyzer(config)
        analyzer.load_model(model_path)
        stats, issues = analyzer.analyze_model()
        
        # Generate detailed report
        report = analyzer.generate_report()
        
        # Check if part is manufacturable based on printability score
        is_manufacturable = True
        critical_issues = []
        warnings = []
        
        for issue in issues:
            if issue["severity"] == "critical":
                is_manufacturable = False
                critical_issues.append({
                    "type": issue["type"],
                    "severity": "critical",
                    "description": issue["details"]
                })
            elif issue["severity"] == "warning":
                warnings.append({
                    "type": issue["type"],
                    "severity": "warning",
                    "description": issue["details"]
                })
        
        # Extract results from report
        final_price = stats["total_cost"]
        lead_time_days = 3  # Default
        
        # Estimate lead time based on print time
        if "estimated_print_time" in stats and stats["estimated_print_time"] != "N/A":
            # Parse print time string (format like "9h 1m")
            print_time_str = stats["estimated_print_time"]
            hours = 0
            minutes = 0
            
            if "h" in print_time_str:
                hours_part = print_time_str.split("h")[0].strip()
                hours = int(hours_part) if hours_part.isdigit() else 0
            
            if "m" in print_time_str:
                minutes_part = print_time_str.split("m")[0].split("h")[-1].strip()
                minutes = int(minutes_part) if minutes_part.isdigit() else 0
            
            # Calculate lead time in days based on print time
            print_time_hours = hours + (minutes / 60)
            if print_time_hours < 12:
                lead_time_days = 2
            elif print_time_hours < 24:
                lead_time_days = 3
            elif print_time_hours < 48:
                lead_time_days = 4
            else:
                lead_time_days = 7
        
        # Return analysis results
        return {
            "is_manufacturable": is_manufacturable,
            "basic_price": final_price,
            "lead_time_days": lead_time_days,
            "printability_score": stats.get("printability_score", 0.0),
            "estimated_print_time": stats.get("estimated_print_time", "N/A"),
            "material_usage_g": stats.get("material_usage_g", 0.0),
            "material_cost": stats.get("material_cost", 0.0),
            "issues": critical_issues + warnings,
            "bounding_box": stats.get("bounding_box", {
                "width": 0,
                "depth": 0,
                "height": 0
            }),
            "volume_mm3": stats.get("volume_mm3", 0.0),
            "volume_cm3": stats.get("volume_cm3", 0.0),
            "surface_area_mm2": stats.get("surface_area_mm2", 0.0)
        }
    except Exception as e:
        logger.error(f"Error in 3D printing DFM analysis: {str(e)}")
        # Return minimal information with error
        return {
            "is_manufacturable": False,
            "basic_price": 0.0,
            "lead_time_days": 0,
            "issues": [{
                "type": "error",
                "severity": "critical",
                "description": f"Analysis error: {str(e)}"
            }]
        }

# Run the application
if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    
    # Add parent directory to path to make imports work correctly when run as script
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Run with the correct module path
    uvicorn.run("dfm.manufacturing_dfm_api:app", host="0.0.0.0", port=8000, reload=True)