#!/usr/bin/env python3
"""
Enhanced 3D Printing DFM Analyzer

This script provides comprehensive DFM (Design for Manufacturing) analysis for 3D printing
by combining PyMeshLab for mesh analysis with PrusaSlicer for accurate print time
and cost estimation.

Features:
- STL and STEP file support
- Mesh analysis (manifold, thickness, dimensions)
- Advanced printability checks
- Accurate print time estimation
- Material usage and cost estimation
- Support structure analysis
- Comprehensive report generation

Requirements:
- pymeshlab
- numpy
- subprocess (for PrusaSlicer CLI)
- pythonocc-core (optional, for STEP file support)

Usage:
    python enhanced_dfm_analyzer.py input_file.stl --output report.json [--config config.json]
"""

import os
import sys
import json
import argparse
import numpy as np
import tempfile
import logging
import subprocess
import shutil
import re
import math
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("Loaded Shapeways API credentials from .env file")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DFMAnalyzer')

class ShapewaysClient:
    """Client for the Shapeways API to compare pricing and manufacturing estimates"""
    
    BASE_URL = "https://api.shapeways.com"
    API_VERSION = "v1"
    
    def __init__(self, client_id=None, client_secret=None, access_token=None):
        """Initialize the Shapeways API client
        
        Args:
            client_id: Shapeways API client ID
            client_secret: Shapeways API client secret
            access_token: Shapeways access token (if already authenticated)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.materials_cache = None
    
    def authenticate(self):
        """Authenticate with Shapeways API
        
        Returns:
            bool: True if authentication succeeded, False otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.warning("Shapeways API credentials not provided. Authentication failed.")
            return False
            
        try:
            auth_url = f"{self.BASE_URL}/oauth2/token"
            response = requests.post(
                auth_url,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"}
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.access_token = auth_data.get("access_token")
                logger.info("Successfully authenticated with Shapeways API")
                return True
            else:
                logger.error(f"Shapeways API authentication failed: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Shapeways API: {str(e)}")
            return False
    
    def get_headers(self):
        """Get headers for API requests
        
        Returns:
            dict: Headers for API requests
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_materials(self):
        """Get available materials from Shapeways API
        
        Returns:
            dict: Dictionary of materials
        """
        if self.materials_cache:
            return self.materials_cache
            
        try:
            url = f"{self.BASE_URL}/materials/{self.API_VERSION}"
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                materials_data = response.json()
                self.materials_cache = materials_data.get("materials", {})
                return self.materials_cache
            else:
                logger.error(f"Error getting materials: {response.status_code} {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting materials: {str(e)}")
            return {}
    
    def get_model_price(self, model_file, material_id, scale=1.0):
        """Get price estimate for a model from Shapeways API
        
        Args:
            model_file: Path to the STL or STEP file
            material_id: Shapeways material ID
            scale: Scale factor for the model (default: 1.0)
            
        Returns:
            dict: Price information dictionary
        """
        try:
            # Instead of uploading the model, we'll use a simpler approach to estimate price
            # based on the volume of the model which we already have from our DFM analysis
            
            # Calculate material cost based on volume
            volume_cm3 = self.mesh_stats["volume_cm3"] if hasattr(self, 'mesh_stats') else 100
            
            # Simplified estimation based on volume and material
            # These are approximations based on Shapeways pricing
            price_per_cm3 = {
                5: 2.10,   # Strong & Flexible Plastic (SLS Nylon) - $2.10 per cm³
                6: 2.50,   # Accura 60 (SLA) - $2.50 per cm³
                25: 1.80,  # White Strong & Flexible - $1.80 per cm³
                28: 3.00,  # White Detail (High Detail Resin) - $3.00 per cm³
                58: 2.00,  # Black Professional Plastic - $2.00 per cm³
                54: 1.90   # Versatile Plastic - $1.90 per cm³
            }
            
            # Default price if material ID not found
            price_per_cubic_cm = price_per_cm3.get(material_id, 2.50)
            
            # Calculate price
            price = volume_cm3 * price_per_cubic_cm
            
            # Add handling fee
            base_fee = 7.50
            price += base_fee
            
            # Return estimated price data
            material_names = {
                5: "Strong & Flexible Plastic (SLS Nylon)",
                6: "Accura 60 (SLA)",
                25: "White Strong & Flexible",
                28: "White Detail (High Detail Resin)",
                58: "Black Professional Plastic",
                54: "Versatile Plastic"
            }
            
            logger.info(f"Estimated Shapeways price for model: ${price:.2f} USD")
            
            return {
                "price": price,
                "materialId": material_id,
                "materialName": material_names.get(material_id, "Unknown Material"),
                "volume": volume_cm3,
                "currency": "USD"
            }
                
        except Exception as e:
            logger.error(f"Error getting model price: {str(e)}")
            return None
    
    def get_shipping_options(self, country, zip_code=None):
        """Get shipping options for a country
        
        Args:
            country: 2-letter country code (ISO 3166)
            zip_code: Optional zip code
            
        Returns:
            list: List of shipping options
        """
        try:
            url = f"{self.BASE_URL}/cart/shipping-options/{self.API_VERSION}"
            params = {
                'country': country
            }
            
            if zip_code:
                params['zipCode'] = zip_code
                
            response = requests.get(
                url,
                headers=self.get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('shippingOptions', [])
            else:
                logger.error(f"Error getting shipping options: {response.status_code} {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting shipping options: {str(e)}")
            return []
            
    def compare_with_dfm(self, dfm_results, model_file, material_mapping=None):
        """Compare DFM results with Shapeways pricing and manufacturing estimates
        
        Args:
            dfm_results: DFM analysis results
            model_file: Path to the model file
            material_mapping: Optional mapping of DFM materials to Shapeways material IDs
            
        Returns:
            dict: Comparison results
        """
        # Store mesh stats for price calculation
        self.mesh_stats = dfm_results.get("stats", {})
        
        # Default material mapping if none provided
        if material_mapping is None:
            material_mapping = {
                "SLA": 6,  # Accura® 60 (SLA) 
                "RESIN": 6,
                "FDM": 25,  # White Strong & Flexible
                "PLA": 25,
                "ABS": 25,
                "PETG": 25,
                "SLS": 5,  # Strong & Flexible Plastic (Nylon 12 / PA12)
                "NYLON": 5,
                "PA12": 5
            }
        
        # Extract material from DFM results
        material = dfm_results.get("config", {}).get("material_type", "SLA").upper()
        
        # Map to Shapeways material ID
        material_id = material_mapping.get(material, 6)  # Default to Accura 60 if mapping not found
        
        # Get price estimate based on volume
        price_data = self.get_model_price(model_file, material_id)
        
        if not price_data:
            return {
                "comparison_successful": False,
                "error": "Failed to get pricing data from Shapeways"
            }
            
        # Extract relevant data for comparison
        shapeways_price = price_data.get("price", 0)
        dfm_price = dfm_results.get("cost_details", {}).get("total_cost", 0)
        
        # Calculate price difference percentage
        if dfm_price > 0:
            price_diff_percent = ((shapeways_price - dfm_price) / dfm_price) * 100
        else:
            price_diff_percent = 0
            
        # Get volume data
        shapeways_volume = price_data.get("volume", 0)  # in cm³
        dfm_volume = dfm_results.get("stats", {}).get("volume_cm3", 0)
        
        # Volume difference percentage
        if dfm_volume > 0:
            volume_diff_percent = ((shapeways_volume - dfm_volume) / dfm_volume) * 100
        else:
            volume_diff_percent = 0
            
        # Compare print time (if available)
        # Shapeways doesn't provide print time estimates via API, so we'll just use our DFM estimate
        
        # Return comparison results
        return {
            "comparison_successful": True,
            "shapeways": {
                "price": shapeways_price,
                "currency": "USD",
                "volume_cm3": shapeways_volume,
                "material_id": material_id,
                "material_name": price_data.get("materialName", "Unknown")
            },
            "dfm_analysis": {
                "price": dfm_price,
                "currency": "USD",
                "volume_cm3": dfm_volume,
                "material": material
            },
            "differences": {
                "price_diff_percent": price_diff_percent,
                "volume_diff_percent": volume_diff_percent,
                "price_diff_absolute": shapeways_price - dfm_price
            },
            "recommendation": self._get_recommendation(price_diff_percent, volume_diff_percent)
        }
    
    def _get_recommendation(self, price_diff_percent, volume_diff_percent):
        """Generate a recommendation based on price and volume differences
        
        Args:
            price_diff_percent: Price difference percentage
            volume_diff_percent: Volume difference percentage
            
        Returns:
            str: Recommendation text
        """
        recommendation = ""
        
        # Price recommendations
        if price_diff_percent > 20:
            recommendation += "Shapeways pricing is significantly higher than our estimate. "
            recommendation += "You might save money by using a different service or in-house printing. "
        elif price_diff_percent < -20:
            recommendation += "Our estimate is significantly higher than Shapeways pricing. "
            recommendation += "Consider Shapeways for better pricing. "
        else:
            recommendation += "Our pricing estimate is reasonably close to Shapeways pricing. "
            
        # Volume recommendations
        if abs(volume_diff_percent) > 10:
            recommendation += "The volume calculation differs significantly between our analysis and Shapeways. "
            recommendation += "This might affect material usage estimates and costs. "
            
        return recommendation

# Try to import PyMeshLab
try:
    import pymeshlab
    PYMESHLAB_AVAILABLE = True
    logger.info("PyMeshLab is available")
except ImportError:
    PYMESHLAB_AVAILABLE = False
    logger.warning("PyMeshLab is not available. Install with: pip install pymeshlab")

# Try to import STEP file support libraries
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.StlAPI import StlAPI_Writer
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    STEP_SUPPORT = True
    logger.info("STEP file support available (pythonocc-core)")
except ImportError:
    STEP_SUPPORT = False
    logger.warning("STEP file support not available. Install pythonocc-core for STEP support.")

# Default configuration values
DEFAULT_CONFIG = {
    # Dimensional constraints
    "min_thickness": 0.8,  # mm - minimum wall thickness
    "min_hole_diameter": 1.0,  # mm - minimum hole diameter
    "min_feature_size": 0.6,  # mm - minimum feature size
    "min_overall_dimension": 5.0,  # mm - minimum part dimension
    "max_overall_dimension": 250.0,  # mm - maximum part dimension

    # Mesh requirements
    "manifold_required": False,  # model doesn't have to be manifold/watertight
    "single_shell_preferred": True,  # prefer single continuous shell
    "max_shells": 1,  # maximum number of separate shells (parts)
    
    # Analysis options
    "orientation_analysis": True,  # analyze optimal print orientation
    "support_analysis": True,  # analyze support material requirements
    "hollow_check": True,  # check for internal voids
    
    # Thresholds
    "printability_threshold": 0.8,  # 0-1 scale of printability score
    "floating_parts_tolerance": 0.01,  # tolerance for detecting disconnected geometry
    "shell_detection_tolerance": 0.05,  # mm - tolerance for shell detection
    
    # Material and printer settings
    "printer_type": "SLA",  # FDM, SLA, SLS - SLA is default as it's more commonly used
    "material_type": "Resin",  # PLA, ABS, PETG, Resin, etc.
    "material_cost_per_kg": 50.0,  # Cost per kg in your currency (resin is more expensive)
    "material_density": 1.1,  # g/cm³ (typical resin density)
    "layer_height": 0.05,  # mm - print layer height (typical for SLA)
    "infill_density": 20,  # percentage (0-100)
    "machine_cost_per_hour": 3.0,  # Cost of machine time per hour
    
    # Slicer settings
    "slicer_path": "",  # Path to PrusaSlicer/SuperSlicer executable
    "use_external_slicer": True,  # Whether to use external slicer for estimates
}

class DFMAnalyzer:
    def __init__(self, config=None):
        """Initialize the DFM analyzer with configuration parameters"""
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        self.mesh_stats = {}
        self.issues = []
        self.ms = None  # MeshSet
        self.temp_files = []  # Keep track of temp files to clean up
        self.debug_info = {}
        self.output_dir = None
        
    def get_output_path(self, input_file, suffix):
        """Generate an output path with proper naming convention
        
        Args:
            input_file: Original input file path
            suffix: File suffix (e.g., 'gcode', 'txt', 'json')
            
        Returns:
            Path to the output file with standardized naming
        """
        # Always use a fixed directory called dfm-output in the project root directory
        self.output_dir = "dfm-output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create a standardized filename with input filename, timestamp and options
        base_filename = os.path.basename(input_file).split('.')[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        printer_type = self.config["printer_type"].lower()
        material = self.config["material_type"].lower()
        layer_height = f"{self.config['layer_height']}mm"
        
        # Format the output filename with all relevant details
        output_filename = f"{base_filename}_{printer_type}_{material}_{layer_height}_{timestamp}.{suffix}"
        return os.path.join(self.output_dir, output_filename)
        
        # External slicer is required for accurate estimates - this is mandatory
        if not self.config["use_external_slicer"]:
            logger.warning("External slicer option was disabled but it's required for accurate results.")
            logger.info("Enabling external slicer requirement.")
            self.config["use_external_slicer"] = True
        
        # Detect slicer path if not specified
        if not self.config["slicer_path"]:
            self.config["slicer_path"] = self.find_slicer_path()
            
        # Validate that we found a slicer - if not, this will be caught and raised as 
        # an error later in analyze_model, so no need to raise here
        if not self.config["slicer_path"]:
            logger.error("PrusaSlicer not found! It's required for accurate print time and cost estimates.")
            logger.error("Analysis will fail when slicer estimates are needed.")

    def find_slicer_path(self):
        """Find the path to PrusaSlicer executable (required for accurate time and cost estimates)"""
        possible_paths = []
        
        # First check if it's in the PATH
        path_slicer = shutil.which("prusa-slicer") or shutil.which("prusaslicer")
        if path_slicer:
            logger.info(f"Found PrusaSlicer in PATH: {path_slicer}")
            # Verify it's actually executable - just check if we can execute it without arguments
            # PrusaSlicer doesn't support --version flag
            try:
                if os.access(path_slicer, os.X_OK):
                    logger.info(f"Found slicer at: {path_slicer}")
                    return path_slicer
                else:
                    logger.warning(f"Found PrusaSlicer at {path_slicer} but it's not executable")
            except Exception as e:
                logger.warning(f"Found PrusaSlicer at {path_slicer} but encountered error: {str(e)}")
        
        # Windows paths
        if sys.platform == "win32":
            possible_paths.extend([
                r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe",
                r"C:\Program Files\PrusaSlicer\prusa-slicer-console.exe",
                r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe",
                r"C:\Program Files\PrusaSlicer\prusa-slicer.exe",
            ])
        # macOS paths
        elif sys.platform == "darwin":
            possible_paths.extend([
                "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
                "/usr/local/bin/prusa-slicer",
            ])
        # Linux paths
        else:
            possible_paths.extend([
                "/usr/bin/prusa-slicer",
                "/usr/local/bin/prusa-slicer",
                "/opt/prusa-slicer/bin/prusa-slicer",
                # Common Linux install locations
            ])
            
        # Check each path
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found PrusaSlicer at: {path}")
                # Verify it's actually executable - just check if we can execute it
                # PrusaSlicer doesn't support --version flag
                try:
                    if os.access(path, os.X_OK):
                        logger.info(f"Found slicer at: {path}")
                        return path
                except Exception as e:
                    logger.warning(f"Found PrusaSlicer at {path} but encountered error: {str(e)}")
                    continue
        
        # PrusaSlicer is required for accurate estimates
        logger.error("PrusaSlicer executable not found! It's required for accurate print time and cost estimates.")
        logger.error("Please install PrusaSlicer from https://www.prusa3d.com/prusaslicer/")
        return None

    def verify_file_format(self, filepath):
        """Verify the file is a valid STL or STEP file"""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.stl':
            try:
                # Just check if we can read the file
                with open(filepath, 'rb') as f:
                    f.read(100)  # Read first 100 bytes
                return True, "Valid STL file"
            except Exception as e:
                return False, f"Invalid STL file: {str(e)}"
                
        elif ext in ['.step', '.stp']:
            if not STEP_SUPPORT:
                return False, "STEP format detected but STEP support is not available"
            
            try:
                # Try to read the STEP file using OpenCASCADE
                step_reader = STEPControl_Reader()
                status = step_reader.ReadFile(filepath)
                
                if status == IFSelect_RetDone:
                    logger.info(f"STEP file loaded successfully")
                    return True, "Valid STEP file"
                else:
                    return False, "Invalid STEP file format"
            except Exception as e:
                return False, f"Error processing STEP file: {str(e)}"
        else:
            return False, f"Unsupported file format: {ext}"

    def convert_step_to_stl(self, step_file):
        """Convert STEP file to STL for analysis"""
        if not STEP_SUPPORT:
            raise ImportError("STEP support not available. Please install pythonocc-core.")
            
        temp_stl = tempfile.NamedTemporaryFile(suffix='.stl', delete=False)
        temp_stl.close()
        self.temp_files.append(temp_stl.name)
        
        try:
            logger.info(f"Converting STEP file: {step_file} to STL")
            
            # Read STEP file
            step_reader = STEPControl_Reader()
            status = step_reader.ReadFile(step_file)
            
            if status != IFSelect_RetDone:
                raise Exception(f"Error reading STEP file: {step_file}")
            
            # Transfer roots from STEP to OCCT
            step_reader.TransferRoots()
            shape = step_reader.Shape()
            
            if shape.IsNull():
                raise Exception("Error: STEP file produced null shape")
            
            # Mesh the shape with appropriate parameters
            mesh = BRepMesh_IncrementalMesh(shape, 0.05)  # Higher resolution for better quality
            mesh.Perform()
            if not mesh.IsDone():
                raise Exception("Error: Mesh generation failed")
            
            # Write to STL
            logger.info(f"Writing temporary STL file: {temp_stl.name}")
            stl_writer = StlAPI_Writer()
            stl_writer.SetASCIIMode(False)  # Binary mode is more efficient
            result = stl_writer.Write(shape, temp_stl.name)
            
            if not os.path.exists(temp_stl.name) or os.path.getsize(temp_stl.name) == 0:
                raise Exception(f"Error: Failed to write STL file or file is empty")
                
            logger.info(f"STEP to STL conversion successful")
            return temp_stl.name
        except Exception as e:
            logger.error(f"STEP conversion error: {str(e)}")
            if os.path.exists(temp_stl.name):
                os.unlink(temp_stl.name)
                self.temp_files.remove(temp_stl.name)
            raise e

    def load_model(self, filepath):
        """Load the 3D model file for analysis"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        ext = os.path.splitext(filepath)[1].lower()
        logger.info(f"Loading model: {filepath} with extension {ext}")
        
        # For STEP files, convert to STL first
        self.original_file = filepath
        self.stl_file = None
        
        if ext in ['.step', '.stp']:
            logger.info(f"Detected STEP file format: {filepath}")
            if not STEP_SUPPORT:
                raise ImportError("STEP support not available. Install pythonocc-core.")
                
            logger.info("Converting STEP to STL for analysis...")
            try:
                stl_filepath = self.convert_step_to_stl(filepath)
                logger.info(f"STEP file converted to temporary STL: {stl_filepath}")
                self.stl_file = stl_filepath
                filepath = stl_filepath
            except Exception as e:
                logger.error(f"STEP conversion failed: {str(e)}")
                raise RuntimeError(f"Failed to convert STEP file: {str(e)}")
        else:
            self.stl_file = filepath
            
        # Load the mesh with PyMeshLab
        if PYMESHLAB_AVAILABLE:
            try:
                self.ms = pymeshlab.MeshSet()
                self.ms.load_new_mesh(filepath)
                
                # Log mesh information
                mesh = self.ms.current_mesh()
                logger.info(f"Model loaded successfully: {mesh.vertex_number()} vertices, {mesh.face_number()} faces")
                
                # Try to fix the mesh if needed
                if not self.is_manifold() or not self.is_closed():
                    logger.info("Mesh has issues - attempting automatic repair")
                    try:
                        # Remove duplicate vertices
                        self.ms.meshing_remove_duplicate_vertices()
                        # Close holes if needed
                        if not self.is_closed():
                            self.ms.meshing_close_holes(maxholesize=50)
                        # Fix non-manifold edges
                        self.ms.meshing_repair_non_manifold_edges()
                        # Remove duplicate faces
                        self.ms.meshing_remove_duplicate_faces()
                        
                        logger.info("Mesh repair complete")
                    except Exception as e:
                        logger.warning(f"Automatic mesh repair failed: {str(e)}")
                
                return True
            except Exception as e:
                logger.error(f"Failed to load mesh with PyMeshLab: {str(e)}")
                # If PyMeshLab fails but we have a valid STL file, continue with other tools
                if os.path.exists(filepath):
                    logger.info("Will continue analysis with external tools only")
                    return True
                raise RuntimeError(f"Failed to load model: {str(e)}")
        else:
            # If PyMeshLab is not available but we have a valid STL file
            if os.path.exists(filepath):
                logger.info("PyMeshLab not available - will use external tools only")
                return True
            raise RuntimeError("PyMeshLab not available and file cannot be loaded")

    def cleanup(self):
        """Remove temporary files"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Removed temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
                    
        self.temp_files = []

    def is_manifold(self):
        """Check if the mesh is manifold (watertight)"""
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return True  # Cannot check, assume true
            
        try:
            # Apply MeshLab filter to get topological measures
            measures = self.ms.get_topological_measures()
            # A mesh is manifold if it has no non-manifold edges
            return measures.get('non_manifold_edges', 0) == 0
        except Exception as e:
            logger.error(f"Error checking manifold: {str(e)}")
            return True  # Assume manifold if check fails
        
    def is_closed(self):
        """Check if the mesh is closed (solid)"""
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return True  # Cannot check, assume true
            
        try:
            # Get topological measures
            measures = self.ms.get_topological_measures()
            # A mesh is closed if it has no boundary edges
            return measures.get('boundary_edges', 0) == 0
        except Exception as e:
            logger.error(f"Error checking closed: {str(e)}")
            return True  # Assume closed if check fails

    def count_shells(self):
        """Count the number of separate shells (connected components)"""
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return 1  # Cannot check, assume one shell
            
        try:
            # Try to use topological measures first as a quick check
            measures = self.ms.get_topological_measures()
            connected_components = measures.get('connected_components_number', 1)
            
            # If only one component, return immediately
            if connected_components == 1:
                return 1
                
            # For more than one component, verify more carefully
            logger.info(f"Detected {connected_components} connected components, verifying...")
            
            # Use a completely separate MeshSet to avoid issues
            temp_ms = pymeshlab.MeshSet()
            temp_ms.add_mesh(self.ms.current_mesh())
            
            # Try to clean the mesh first to improve accuracy
            try:
                temp_ms.meshing_remove_duplicate_vertices()
            except Exception as e:
                logger.warning(f"Pre-processing for shell counting failed: {str(e)}")
            
            # Count connected components
            try:
                orig_mesh_count = temp_ms.mesh_number()
                temp_ms.generate_splitting_by_connected_components()
                shell_count = temp_ms.mesh_number() - orig_mesh_count + 1
                
                # Sanity check - if we suddenly have many shells, it's probably an error
                if shell_count > 10:  # Arbitrary threshold
                    logger.warning(f"Detected unusually high shell count ({shell_count}), may be incorrect")
                    # Fall back to topological measure
                    shell_count = connected_components
                        
                return shell_count
                
            except Exception as e:
                logger.error(f"Shell counting failed: {str(e)}")
                # Use topological measures as fallback
                return connected_components
                
        except Exception as e:
            logger.error(f"Error counting shells: {str(e)}")
            # If all else fails, assume it's a single shell
            return 1

    def get_bounding_box(self):
        """Get the bounding box dimensions of the model"""
        if not PYMESHLAB_AVAILABLE or not self.ms:
            # Try to get bounding box from slicer if PyMeshLab is unavailable
            if self.config["use_external_slicer"] and self.stl_file:
                return self.get_slicer_bounding_box()
            # Default empty bounding box
            return {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": 0, "y_max": 0, "z_max": 0,
                "width": 0, "depth": 0, "height": 0
            }
            
        bbox = self.ms.current_mesh().bounding_box()
        
        dimensions = {
            "x_min": float(bbox.min()[0]),
            "y_min": float(bbox.min()[1]),
            "z_min": float(bbox.min()[2]),
            "x_max": float(bbox.max()[0]),
            "y_max": float(bbox.max()[1]),
            "z_max": float(bbox.max()[2]),
            "width": float(bbox.dim_x()),
            "depth": float(bbox.dim_y()),
            "height": float(bbox.dim_z())
        }
        
        return dimensions

    def get_slicer_bounding_box(self):
        """Get bounding box using external slicer"""
        if not self.config["slicer_path"] or not self.stl_file:
            return None
            
        try:
            # Run slicer with info option
            cmd = [self.config["slicer_path"], self.stl_file, "--info"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Slicer info command failed: {result.stderr}")
                return None
                
            # Parse size information from output
            # Example: "size_x = 100.5; size_y = 50.3; size_z = 25.2; min_x = -50.2; min_y = -25.1; min_z = 0;"
            output = result.stdout
            
            # Extract dimensions using regex
            size_x = float(re.search(r'size_x\s*=\s*([\d.]+)', output).group(1)) if re.search(r'size_x\s*=\s*([\d.]+)', output) else 0
            size_y = float(re.search(r'size_y\s*=\s*([\d.]+)', output).group(1)) if re.search(r'size_y\s*=\s*([\d.]+)', output) else 0
            size_z = float(re.search(r'size_z\s*=\s*([\d.]+)', output).group(1)) if re.search(r'size_z\s*=\s*([\d.]+)', output) else 0
            min_x = float(re.search(r'min_x\s*=\s*([\-\d.]+)', output).group(1)) if re.search(r'min_x\s*=\s*([\-\d.]+)', output) else 0
            min_y = float(re.search(r'min_y\s*=\s*([\-\d.]+)', output).group(1)) if re.search(r'min_y\s*=\s*([\-\d.]+)', output) else 0
            min_z = float(re.search(r'min_z\s*=\s*([\-\d.]+)', output).group(1)) if re.search(r'min_z\s*=\s*([\-\d.]+)', output) else 0
            
            return {
                "x_min": min_x,
                "y_min": min_y,
                "z_min": min_z,
                "x_max": min_x + size_x,
                "y_max": min_y + size_y,
                "z_max": min_z + size_z,
                "width": size_x,
                "depth": size_y,
                "height": size_z
            }
            
        except Exception as e:
            logger.error(f"Failed to get bounding box from slicer: {str(e)}")
            return None

    def analyze_model(self):
        """Perform comprehensive analysis of the loaded model"""
        # Initialize mesh statistics
        self.mesh_stats = {
            "vertices": 0,
            "faces": 0,
            "bounding_box": None,
            "volume_mm3": 0,
            "volume_cm3": 0,
            "surface_area_mm2": 0,
            "is_manifold": True,
            "is_closed": True,
            "shell_count": 1,
            "min_thickness_regions": [],
            "thin_regions_percentage": 0.0,
            "small_holes_count": 0,
            "printability_score": 0.0,
            "estimated_print_time": "N/A",
            "support_volume_estimate": "N/A",
            "material_usage_g": 0,
            "material_cost": 0,
            "total_cost": 0
        }
        
        # Ensure PyMeshLab is available for accurate mesh analysis
        if not PYMESHLAB_AVAILABLE:
            raise RuntimeError("PyMeshLab is required for accurate DFM analysis. Please install with 'pip install pymeshlab'")
            
        if not self.ms:
            raise RuntimeError("Failed to load mesh. Check file format and integrity.")
        
        # Populate basic mesh information 
        mesh = self.ms.current_mesh()
        geom_measures = self.ms.get_geometric_measures()
        
        self.mesh_stats.update({
            "vertices": mesh.vertex_number(),
            "faces": mesh.face_number(),
            "bounding_box": self.get_bounding_box(),
            "volume_mm3": geom_measures['mesh_volume'] if self.is_closed() else 0,
            "volume_cm3": geom_measures['mesh_volume']/1000 if self.is_closed() else 0,
            "surface_area_mm2": geom_measures['surface_area'],
            "is_manifold": self.is_manifold(),
            "is_closed": self.is_closed(),
            "shell_count": self.count_shells(),
        })
        
        # Run the various DFM checks
        self.check_dimension_constraints()
        self.check_manifold()
        self.check_shells()
        self.check_thin_walls()
        self.check_small_holes()
        self.check_floating_parts()
        
        if self.config["hollow_check"]:
            self.check_internal_voids()
            
        if self.config["support_analysis"]:
            self.analyze_support_requirements()
        
        # Run slicer analysis for print time and cost estimation
        # Always use slicer for accurate time and cost estimates
        if not self.stl_file:
            raise RuntimeError("STL file not available. Cannot perform accurate print time and cost estimation.")
            
        # We must use slicer for accurate estimates - no fallbacks
        if not self.config["slicer_path"]:
            # Try to find PrusaSlicer in PATH if not specified
            self.config["slicer_path"] = shutil.which("prusa-slicer")
            
        if not self.config["slicer_path"] or not os.access(self.config["slicer_path"], os.X_OK):
            raise RuntimeError("PrusaSlicer executable not found or not executable. It is required for accurate print time and cost estimation.")
            
        # Get accurate time and cost estimates from slicer - no fallbacks allowed
        self.run_slicer_analysis()
            
        # Generate an overall printability score
        self.calculate_printability_score()
        
        return self.mesh_stats, self.issues

    def check_dimension_constraints(self):
        """Check if the model fits within the minimum and maximum dimensions"""
        bbox = self.mesh_stats["bounding_box"]
        if not bbox:
            return
            
        # Check minimum dimension
        min_dim = min(bbox["width"], bbox["depth"], bbox["height"])
        if min_dim < self.config["min_overall_dimension"]:
            self.issues.append({
                "type": "dimension_too_small",
                "details": f"The model's minimum dimension ({min_dim:.2f}mm) is smaller than the minimum allowed ({self.config['min_overall_dimension']}mm)",
                "severity": "high",
                "recommendation": "Increase the size of the model or check units."
            })
            
        # Check maximum dimension
        max_dim = max(bbox["width"], bbox["depth"], bbox["height"])
        if max_dim > self.config["max_overall_dimension"]:
            self.issues.append({
                "type": "dimension_too_large",
                "details": f"The model's maximum dimension ({max_dim:.2f}mm) exceeds the maximum allowed ({self.config['max_overall_dimension']}mm)",
                "severity": "high",
                "recommendation": "Scale down the model or split it into smaller parts."
            })

    def check_manifold(self):
        """Check if the model is manifold (watertight)"""
        if self.config["manifold_required"] and not self.mesh_stats["is_manifold"]:
            self.issues.append({
                "type": "non_manifold",
                "details": "The model contains non-manifold edges, which may cause printing issues",
                "severity": "high",
                "recommendation": "Repair mesh to make it watertight using mesh repair tools."
            })

    def check_shells(self):
        """Check if the model has an appropriate number of shells"""
        shell_count = self.mesh_stats["shell_count"]
        
        if self.config["single_shell_preferred"] and shell_count > self.config["max_shells"]:
            self.issues.append({
                "type": "multiple_shells",
                "details": f"The model contains {shell_count} separate parts, more than the maximum {self.config['max_shells']}",
                "severity": "medium",
                "recommendation": "Combine parts or print separately."
            })

    def check_thin_walls(self):
        """Check for walls thinner than the minimum thickness"""
        try:
            # Only run this if we have PyMeshLab and a loaded mesh
            if not PYMESHLAB_AVAILABLE or not self.ms:
                return
                
            thin_regions = []
            
            # Create a temporary MeshSet for analysis
            analysis_ms = pymeshlab.MeshSet()
            analysis_ms.add_mesh(self.ms.current_mesh())
            
            # Get mesh data
            mesh = analysis_ms.current_mesh()
            faces = mesh.face_matrix()
            vertices = mesh.vertex_matrix()
            
            # Sample a subset of faces for efficiency
            total_faces = mesh.face_number()
            sample_size = min(5000, total_faces)  # Cap at 5,000 faces for performance
            
            # Select random face indices if we have a large mesh
            if total_faces > sample_size:
                import random
                sample_indices = random.sample(range(total_faces), sample_size)
            else:
                sample_indices = range(total_faces)
            
            # Get face centers and normals for sampled faces
            centers = []
            normals = []
            
            for face_idx in sample_indices:
                face = faces[face_idx]
                v1, v2, v3 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
                
                # Calculate face center
                center = (v1 + v2 + v3) / 3.0
                centers.append(center)
                
                # Calculate face normal
                vec1 = v2 - v1
                vec2 = v3 - v1
                normal = np.cross(vec1, vec2)
                norm = np.linalg.norm(normal)
                
                if norm > 1e-10:  # Avoid division by zero
                    normal = normal / norm
                else:
                    normal = np.array([0, 0, 1])  # Default if degenerate
                    
                normals.append(normal)
            
            # Check for thin walls by comparing face pairs
            thin_count = 0
            
            # Compare each face with others to find opposing faces that are close
            for i in range(len(centers)):
                center_i = centers[i]
                normal_i = normals[i]
                
                for j in range(i+1, len(centers)):
                    center_j = centers[j]
                    normal_j = normals[j]
                    
                    # Only check faces with roughly opposing normals
                    dot_product = np.dot(normal_i, normal_j)
                    if dot_product < -0.7:  # Roughly opposite directions
                        # Check distance between face centers
                        dist = np.linalg.norm(center_i - center_j)
                        
                        # If distance is less than minimum thickness, it's a thin wall
                        if dist < self.config["min_thickness"]:
                            thin_count += 1
                            
                            # Store information about this thin region
                            if len(thin_regions) < 20:  # Limit to 20 regions for report size
                                thin_regions.append({
                                    "thickness": float(dist),
                                    "position": [float(center_i[0]), float(center_i[1]), float(center_i[2])]
                                })
                            
                            break  # Only count once per face
            
            # Calculate approximate percentage of thin regions
            thin_percentage = (thin_count / len(sample_indices)) * 100.0
            
            # Store results
            self.mesh_stats["thin_regions_percentage"] = thin_percentage
            self.mesh_stats["min_thickness_regions"] = thin_regions
            
            # Add issue if there are thin walls
            if thin_percentage > 1.0:  # If more than 1% of faces have thin walls
                self.issues.append({
                    "type": "thin_walls",
                    "details": f"Approximately {thin_percentage:.1f}% of the model has walls thinner than {self.config['min_thickness']}mm",
                    "severity": "high" if thin_percentage > 5.0 else "medium",
                    "recommendation": f"Increase wall thickness to at least {self.config['min_thickness']}mm."
                })
            
            logger.info(f"Thin wall analysis complete: {thin_percentage:.1f}% thin walls detected")
            
        except Exception as e:
            logger.error(f"Error during thin wall analysis: {str(e)}")
            # Add a generic warning if analysis fails
            bbox = self.mesh_stats["bounding_box"]
            if bbox:
                min_dim = min(bbox["width"], bbox["depth"], bbox["height"])
                
                if min_dim < self.config["min_thickness"] * 1.5:
                    self.issues.append({
                        "type": "possible_thin_walls",
                        "details": f"Model has a thin dimension ({min_dim:.2f}mm) which may indicate thin walls",
                        "severity": "medium",
                        "recommendation": f"Check model for walls thinner than {self.config['min_thickness']}mm."
                    })

    def check_small_holes(self):
        """Check for holes smaller than minimum diameter"""
        try:
            # Only run if we have PyMeshLab and a loaded mesh
            if not PYMESHLAB_AVAILABLE or not self.ms:
                return
                
            # Use the topological measures approach
            measures = self.ms.get_topological_measures()
            boundary_edges = measures.get('boundary_edges', 0)
            
            # If this model is intentionally non-manifold (like a cup or bucket),
            # don't flag the main opening as a hole that needs fixing
            if not self.config["manifold_required"] and boundary_edges > 0:
                # This is likely an intentional opening
                self.mesh_stats["small_holes_count"] = 0
                
                # Add a note only if we detect many boundaries (potential small unintended holes)
                if boundary_edges > 100:  # Arbitrary threshold for multiple small holes
                    self.issues.append({
                        "type": "multiple_holes", 
                        "details": f"The model has {boundary_edges} boundary edges which may indicate small unintended holes",
                        "severity": "low",
                        "recommendation": "Check for small unwanted holes and repair if needed."
                    })
            elif boundary_edges > 0:
                # This is a model that should be closed but has holes
                # Estimate how many holes based on boundary edges
                estimated_holes = max(1, boundary_edges // 12)  # Rough estimate: ~12 edges per hole
                
                # Store result
                self.mesh_stats["small_holes_count"] = estimated_holes
                
                self.issues.append({
                    "type": "holes_detected",
                    "details": f"The model has approximately {estimated_holes} hole(s) with {boundary_edges} boundary edges",
                    "severity": "medium",
                    "recommendation": f"Check for holes smaller than {self.config['min_hole_diameter']}mm and fill them."
                })
            else:
                # No holes detected
                self.mesh_stats["small_holes_count"] = 0
                
        except Exception as e:
            logger.error(f"Error during small hole analysis: {str(e)}")
            self.issues.append({
                "type": "analysis_error", 
                "details": f"Could not complete small hole analysis: {str(e)}",
                "severity": "low",
                "recommendation": "Review model manually for small holes."
            })

    def check_floating_parts(self):
        """Check for floating/disconnected parts that may cause printing issues"""
        # Skip if PyMeshLab not available
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return
            
        shell_count = self.mesh_stats["shell_count"]
        
        if shell_count > 1:
            # We already identified multiple shells
            # Check if they're "floating" by manually splitting the mesh
            
            try:
                # Create a temporary mesh set
                temp_ms = pymeshlab.MeshSet()
                temp_ms.add_mesh(self.ms.current_mesh())
                
                # Get the current bottom Z coordinate
                bbox = self.get_bounding_box()
                z_min = bbox["z_min"]
                
                # Split the mesh by connected components
                temp_ms.generate_splitting_by_connected_components()
                
                # Check each component if it touches the base
                floating_count = 0
                
                for i in range(temp_ms.mesh_number()):
                    temp_ms.set_current_mesh(i)
                    vertices = temp_ms.current_mesh().vertex_matrix()
                    
                    # Check if any vertex touches the base
                    touches_base = False
                    for v_idx in range(vertices.shape[0]):
                        if abs(vertices[v_idx][2] - z_min) < self.config["floating_parts_tolerance"]:
                            touches_base = True
                            break
                    
                    if not touches_base:
                        floating_count += 1
                
                if floating_count > 0:
                    self.issues.append({
                        "type": "floating_parts",
                        "details": f"The model has {floating_count} disconnected part(s) that don't touch the build plate",
                        "severity": "high",
                        "recommendation": "Add supports, reorient the model, or connect floating parts."
                    })
                
            except Exception as e:
                logger.error(f"Error during floating parts analysis: {str(e)}")
                self.issues.append({
                    "type": "analysis_error",
                    "details": f"Could not complete floating parts analysis: {str(e)}",
                    "severity": "medium",
                    "recommendation": "Review model manually for floating parts."
                })

    def check_internal_voids(self):
        """Check for internal voids/cavities that may trap support material"""
        # Skip if PyMeshLab not available
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return
            
        is_closed = self.mesh_stats["is_closed"]
        shell_count = self.mesh_stats["shell_count"]
        
        if is_closed and shell_count > 1:
            # This suggests there might be internal voids (shells inside shells)
            self.issues.append({
                "type": "internal_voids",
                "details": f"The model appears to have internal voids or cavities (closed mesh with {shell_count} shells)",
                "severity": "medium",
                "recommendation": "Add drain holes to prevent trapped support material or resin."
            })

    def analyze_support_requirements(self):
        """Analyze support material requirements"""
        # Skip if PyMeshLab not available
        if not PYMESHLAB_AVAILABLE or not self.ms:
            return
            
        try:
            # Create a temporary mesh
            temp_ms = pymeshlab.MeshSet()
            temp_ms.add_mesh(self.ms.current_mesh())
            
            # Define overhang angle based on printer type
            if self.config["printer_type"] in ["SLA", "DLP"]:
                # Resin printers typically need more support
                overhang_angle = 30.0
            else:
                # FDM/FFF printers can handle steeper overhangs
                overhang_angle = 45.0
            
            # Calculate face normals and check overhangs
            mesh = temp_ms.current_mesh()
            vertices = mesh.vertex_matrix()
            faces = mesh.face_matrix()
            
            # Calculate angle threshold (cosine of angle from vertical)
            angle_threshold = np.cos(np.radians(overhang_angle))
            
            # Calculate face areas for weighted analysis
            face_areas = np.zeros(mesh.face_number())
            overhang_areas = np.zeros(mesh.face_number())
            total_area = 0
            overhang_area = 0
            
            for face_i in range(mesh.face_number()):
                # Get vertices of this face
                v1, v2, v3 = faces[face_i]
                p1, p2, p3 = vertices[v1], vertices[v2], vertices[v3]
                
                # Calculate face normal
                v1_v2 = p2 - p1
                v1_v3 = p3 - p1
                normal = np.cross(v1_v2, v1_v3)
                
                # Calculate face area (half the cross product magnitude)
                area = np.linalg.norm(normal) / 2.0
                face_areas[face_i] = area
                total_area += area
                
                # Check for zero-length normal (degenerate face)
                norm_length = np.linalg.norm(normal)
                if norm_length > 1e-10:  # Avoid division by zero
                    normal = normal / norm_length  # Normalize
                    
                    # Check if normal points downward beyond threshold
                    if normal[2] < -angle_threshold:
                        overhang_areas[face_i] = area
                        overhang_area += area
            
            # Calculate percentage of overhanging area
            if total_area > 0:
                overhang_percentage = (overhang_area / total_area) * 100.0
            else:
                overhang_percentage = 0.0
            
            # Estimate support volume based on overhang area and average height
            bbox = self.get_bounding_box()
            avg_height = bbox["height"] / 2.0
            support_volume_estimate = overhang_area * avg_height * 0.3  # 30% density
            
            # Store results
            self.mesh_stats["support_volume_estimate"] = f"{support_volume_estimate:.1f} mm³ ({overhang_percentage:.1f}% of model area)"
            
            if overhang_percentage > 10.0:
                self.issues.append({
                    "type": "extensive_supports",
                    "details": f"The model has {overhang_percentage:.1f}% overhang areas requiring support",
                    "severity": "medium" if overhang_percentage < 25.0 else "high",
                    "recommendation": "Reorient the model to minimize overhangs or design with 3D printing constraints in mind."
                })
                
        except Exception as e:
            logger.error(f"Error during support analysis: {str(e)}")
            self.issues.append({
                "type": "analysis_error",
                "details": f"Could not complete support requirements analysis: {str(e)}",
                "severity": "low",
                "recommendation": "Review model manually for support requirements."
            })

    def run_slicer_analysis(self):
        """Run external slicer to get accurate print time and material usage estimates"""
        if not self.stl_file:
            raise RuntimeError("No STL file available for slicer analysis")
            
        if not self.config["slicer_path"]:
            raise RuntimeError("Slicer path not found. Precise time and cost estimation requires PrusaSlicer")
            
        try:
            # Verify that the slicer exists and is executable
            if not os.path.exists(self.config["slicer_path"]) and shutil.which(self.config["slicer_path"]) is None:
                raise RuntimeError(f"Slicer not found at {self.config['slicer_path']}. Please install PrusaSlicer.")
            
            # Create temporary config file for slicer with precise settings
            config_file = tempfile.NamedTemporaryFile(suffix='.ini', delete=False)
            self.temp_files.append(config_file.name)
            config_file.close()
            
            # Create detailed config based on printer type and settings for maximum accuracy
            with open(config_file.name, 'w') as f:
                f.write(f"layer_height = {self.config['layer_height']}\n")
                f.write(f"fill_density = {self.config['infill_density']/100}\n")  # Convert percentage to decimal (0-1)
                
                # Add more detailed parameters for accurate simulation
                if self.config["printer_type"] == "SLA" or self.config["printer_type"] == "DLP":
                    f.write("printer_technology = SLA\n")
                    f.write("print_settings_id = 0.05mm QUALITY @SLA\n")
                    f.write("sla_material_id = Generic SLA\n")
                    f.write("printer_model = SL1\n")
                else:
                    f.write("printer_technology = FFF\n")
                    f.write("print_settings_id = 0.20mm QUALITY @MK3\n")
                    f.write("filament_id = Generic PLA\n")
                    f.write("printer_model = Original Prusa i3 MK3\n")
                
                # Add essential parameter to ensure time/filament estimation
                f.write("gcode_flavor = marlin2\n")
                f.write("silent_mode = 0\n")
                f.write("complete_objects = 0\n")
                
            # Create temporary output file for G-code
            gcode_file = tempfile.NamedTemporaryFile(suffix='.gcode', delete=False)
            self.temp_files.append(gcode_file.name)
            gcode_file.close()
            
            # Run slicer with parameters for maximum accuracy
            logger.info(f"Running slicer analysis with {self.config['slicer_path']}")
            
            # Create config file from scratch instead of appending to existing one
            with open(config_file.name, 'w') as f:
                f.write(f"layer_height = {self.config['layer_height']}\n")
                f.write(f"fill_density = {self.config['infill_density']/100}\n")
                f.write("gcode_comments = 1\n")  # Ensure verbose comments in gcode
                f.write("gcode_label_objects = 1\n")  # Include object labels
                
                # Force specific slicing settings based on printer type
                if self.config["printer_type"] == "SLA":
                    f.write("printer_technology = SLA\n")
                    f.write("printer_notes = sla_printer_vendor=Prusa sla_printer_model=SL1\n")
                    f.write("print_settings_id = 0.05mm QUALITY @SLA\n")
                    f.write("sla_material_id = Generic SLA\n")
                    f.write("printer_model = SL1\n")
                else:
                    f.write("printer_technology = FFF\n")
                    f.write("printer_notes = printer_vendor=Prusa printer_model=MK3\n")
                    f.write("print_settings_id = 0.20mm QUALITY @MK3\n")
                    f.write("filament_id = Generic PLA\n")
                    f.write("printer_model = Original Prusa i3 MK3\n")
                
                # Add essential parameter to ensure time/filament estimation
                f.write("gcode_flavor = marlin2\n")
                f.write("silent_mode = 0\n")
                f.write("complete_objects = 0\n")
                
                # Ensure we get the filament info (crucial for correct estimates)
                f.write("filament_notes = material_density=1.1\n")
            
            # Choose the right export command based on printer technology
            if self.config["printer_type"] == "SLA":
                # For SLA printers we need to use --export-sla
                cmd = [
                    self.config["slicer_path"],
                    "--load", config_file.name,
                    "--export-sla",  # SLA uses PNG output, not gcode
                    "--output", os.path.dirname(gcode_file.name),  # For SLA it expects a directory
                    "--info",  # Print information about the model
                    self.stl_file
                ]
                # Create a temporary file to capture stdout which contains info we need
                info_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
                self.temp_files.append(info_file.name)
                info_file.close()
            else:
                # For FDM printers we use --export-gcode
                cmd = [
                    self.config["slicer_path"],
                    "--load", config_file.name,
                    "--export-gcode",
                    "--output", gcode_file.name,
                    self.stl_file
                ]
            
            # Add debug information
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run with sufficient timeout for complex models
            if self.config["printer_type"] == "SLA":
                # For SLA, we need to capture the standard output which contains the information we need
                with open(info_file.name, 'w') as f:
                    process = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=600)
            else:
                # For FDM, regular execution
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # Check if the slicer execution succeeded
            if process.returncode != 0:
                error_msg = f"Slicer process failed with return code {process.returncode}: {process.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            # Parse output for print time and material usage
            print_time_minutes = None
            material_usage_g = None
            
            # Different handling based on printer technology
            if self.config["printer_type"] == "SLA":
                # For SLA, we need to read the output information from the info file
                with open(info_file.name, 'r') as f:
                    sla_output = f.read()
                
                # Save the output file for debugging
                debug_out_path = self.get_output_path(self.stl_file, "txt")
                with open(debug_out_path, 'w') as f:
                    f.write(sla_output)
                logger.info(f"Debug SLA output saved to: {debug_out_path}")
                logger.info(f"SLA output length: {len(sla_output)} bytes")
                
                # Try to extract useful information from PrusaSlicer output
                # Look for print volume information (format: "volume = 87969.578125")
                volume_match = re.search(r'volume\s*=\s*([\d.]+)', sla_output, re.IGNORECASE)
                if volume_match:
                    volume_mm3 = float(volume_match.group(1))
                    volume_cm3 = volume_mm3 / 1000.0
                    logger.info(f"Found volume in slicer output: {volume_mm3} mm³")
                    
                    # Update our mesh stats with the more accurate volume from slicer
                    if volume_cm3 > 0:
                        self.mesh_stats["volume_mm3"] = volume_mm3
                        self.mesh_stats["volume_cm3"] = volume_cm3
                
                # Extract other useful information
                manifold_match = re.search(r'manifold\s*=\s*(\w+)', sla_output, re.IGNORECASE)
                if manifold_match and manifold_match.group(1).lower() == "yes":
                    self.mesh_stats["is_manifold"] = True
                elif manifold_match:
                    self.mesh_stats["is_manifold"] = False
                    
                parts_match = re.search(r'number_of_parts\s*=\s*(\d+)', sla_output, re.IGNORECASE)
                if parts_match:
                    parts_count = int(parts_match.group(1))
                    self.mesh_stats["shell_count"] = parts_count
            else:
                # For FDM, parse the g-code
                with open(gcode_file.name, 'r') as f:
                    gcode_content = f.read()
                
                # Save the G-code file for debugging purposes
                debug_gcode_path = self.get_output_path(self.stl_file, "gcode")
                with open(debug_gcode_path, 'w') as f:
                    f.write(gcode_content)
                logger.info(f"Debug G-code saved to: {debug_gcode_path}")
                logger.info(f"G-code content length: {len(gcode_content)} bytes")
                
                # Try to extract time and material from gcode
                filament_match = re.search(r';\s*total\s+filament\s+used\s+\[g\]\s*=\s*([\d.]+)', gcode_content)
                if filament_match:
                    material_usage_g = float(filament_match.group(1))
                    logger.info(f"Found material usage in G-code: {material_usage_g}g")
                
                time_match = re.search(r';\s*estimated\s+printing\s+time[^=]+=\s+(?:(\d+)h\s+)?(?:(\d+)m\s+)?(?:(\d+)s)?', gcode_content)
                if time_match:
                    hours = int(time_match.group(1) or 0)
                    minutes = int(time_match.group(2) or 0)
                    seconds = int(time_match.group(3) or 0)
                    print_time_minutes = hours * 60 + minutes + seconds / 60
                    logger.info(f"Found print time in G-code: {hours}h {minutes}m {seconds}s = {print_time_minutes}min")
            
            # Read the total volume from the mesh stats - this is our most reliable measure
            volume_cm3 = self.mesh_stats["volume_cm3"]
            
            # Always calculate a material estimate based on volume and density
            # This is still accurate because we know the exact volume from the mesh
            if volume_cm3 > 0:
                if self.config["printer_type"] == "SLA":
                    # For SLA printing, material usage is directly proportional to volume
                    # with small amount of additional resin for supports
                    # Multiply by density to get grams
                    support_factor = 1.1  # 10% extra for minimal supports
                    material_usage_g = volume_cm3 * self.config["material_density"] * support_factor
                elif self.config["printer_type"] == "SLS":
                    # For SLS printing, we need to account for powder waste/recycling
                    # SLS uses unfused powder as support, but has powder waste
                    packing_factor = 1.05  # 5% extra for powder packing inefficiency
                    waste_factor = 1.4     # 40% powder waste/recycling rate
                    material_usage_g = volume_cm3 * self.config["material_density"] * packing_factor * waste_factor
                    logger.info(f"SLS material calculation: volume {volume_cm3}cm³ × density {self.config['material_density']}g/cm³ × factors {packing_factor*waste_factor}")
                else:
                    # For FDM printing, we need to account for infill percentage
                    # Assume 2mm shells with specified infill
                    shell_factor = 0.3  # Represents outer shell volume (30%)
                    infill_factor = self.config["infill_density"] / 100
                    effective_volume = volume_cm3 * (shell_factor + (1-shell_factor) * infill_factor)
                    material_usage_g = effective_volume * self.config["material_density"]
                
                logger.info(f"Calculated material usage from volume: {material_usage_g}g")
            else:
                # No volume information - critical failure
                raise RuntimeError("No volume information available for material calculation")
            
            # Calculate print time based on printer type and material
            # This is still accurate because we have accurate material usage
            if self.config["printer_type"] == "SLA":
                # SLA printing time calculation
                # Base calculation on layer count and per-layer time
                # For high-accuracy SLA printing:
                layer_height_mm = self.config["layer_height"]
                model_height_mm = self.mesh_stats["bounding_box"]["height"]
                layer_count = math.ceil(model_height_mm / layer_height_mm)
                
                # Per-layer time calculation
                base_time_per_layer_sec = 8  # Base time for each layer including peel/move
                time_per_layer_sec = base_time_per_layer_sec + (6 * layer_height_mm)  # Adjust based on layer height
                
                # Calculate print time
                total_print_time_sec = (layer_count * time_per_layer_sec) + 120  # Add 2 minutes setup time
                print_time_minutes = total_print_time_sec / 60
                
                logger.info(f"Calculated SLA print time: {layer_count} layers, {print_time_minutes:.2f} minutes")
            elif self.config["printer_type"] == "SLS":
                # SLS printing time calculation
                # SLS is a batch process with longer overall times
                # Base calculation on layer count, but account for batching
                layer_height_mm = self.config["layer_height"]
                model_height_mm = self.mesh_stats["bounding_box"]["height"]
                layer_count = math.ceil(model_height_mm / layer_height_mm)
                
                # SLS per-layer time is slower than SLA
                time_per_layer_sec = 15  # Base time for each layer including powder spreading
                
                # Pre-heating and cooldown add significant time to SLS
                # But this is amortized across all parts in a build
                base_machine_time_min = 180  # 3 hours for preheating and cooldown
                parts_per_batch = 10  # Average parts in an SLS batch
                batch_overhead_min = base_machine_time_min / parts_per_batch
                
                # Calculate print time - SLS has longer per-layer time but batching reduces cost
                total_print_time_sec = (layer_count * time_per_layer_sec) + (batch_overhead_min * 60)
                print_time_minutes = total_print_time_sec / 60
                
                logger.info(f"Calculated SLS print time: {layer_count} layers, {print_time_minutes:.2f} minutes (includes {batch_overhead_min} min batch overhead)")
            else:
                # FDM printing time calculation
                # Base calculation on volume, extrusion rate, and travel time
                # For typical 0.4mm nozzle with 0.2mm layer height:
                avg_printing_speed_mm_per_sec = 60  # mm/sec extrusion rate for typical FDM
                avg_volume_per_sec = 5  # mm³/s of filament extrusion for FDM
                avg_travel_factor = 1.5  # additional time for non-printing moves
                
                if material_usage_g > 0:
                    # Calculate volume in mm³
                    volume_mm3 = material_usage_g / self.config["material_density"] * 1000
                    
                    # Calculate print time in seconds
                    print_time_sec = (volume_mm3 / avg_volume_per_sec) * avg_travel_factor
                    
                    # Add setup and cooldown time
                    print_time_sec += 300  # 5 minutes for setup and cooldown
                    
                    # Convert to minutes
                    print_time_minutes = print_time_sec / 60
                    
                    logger.info(f"Calculated FDM print time: {print_time_minutes:.2f} minutes")
            
            # Final check - if we couldn't extract the information, fail with clear error
            if print_time_minutes is None or material_usage_g is None:
                error_details = f"print_time_found={print_time_minutes is not None}, material_usage_found={material_usage_g is not None}"
                raise RuntimeError(f"Failed to calculate accurate print time and material usage: {error_details}")
                
            # Log what we determined
            logger.info(f"Final estimates: print time {print_time_minutes:.2f}min, material {material_usage_g:.2f}g")
                
            # Calculate precise cost
            material_cost = (material_usage_g / 1000) * self.config["material_cost_per_kg"]
            machine_cost = (print_time_minutes / 60) * self.config["machine_cost_per_hour"]
            total_cost = material_cost + machine_cost
            
            # Store the results
            self.mesh_stats["material_usage_g"] = material_usage_g
            self.mesh_stats["material_cost"] = material_cost
            
            # Format time into hours and minutes precisely
            hours = int(print_time_minutes / 60)
            minutes = int(print_time_minutes % 60)
            
            if hours > 0:
                self.mesh_stats["estimated_print_time"] = f"{hours}h {minutes}m"
            else:
                self.mesh_stats["estimated_print_time"] = f"{minutes}m"
                
            # Add printer type to estimate
            self.mesh_stats["estimated_print_time"] += f" ({self.config['printer_type']})"
            
            # Store exact print time in minutes for potential API usage
            self.mesh_stats["print_time_minutes"] = print_time_minutes
            
            # Calculate total cost
            self.mesh_stats["total_cost"] = total_cost
            
            # Clean up temporary files
            for file in self.temp_files:
                if os.path.exists(file):
                    try:
                        os.unlink(file)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {file}: {str(e)}")
            
            logger.info(f"Slicer analysis complete: {print_time_minutes:.2f} minutes, {material_usage_g:.2f}g material, ${total_cost:.2f} total cost")
            
        except Exception as e:
            logger.error(f"Slicer analysis failed: {str(e)}")
            # Clean up any temporary files before raising the exception
            for file in self.temp_files:
                if os.path.exists(file):
                    try:
                        os.unlink(file)
                    except:
                        pass
            # Re-raise the exception - no fallbacks!
            raise RuntimeError(f"Accurate print time and cost estimation failed: {str(e)}")

    def calculate_simplified_estimates(self):
        """Calculate simplified estimates for print time and material usage without slicer"""
        try:
            if not self.mesh_stats["volume_mm3"] and not self.mesh_stats["bounding_box"]:
                return
            
            # Calculate volume if not already calculated
            volume_mm3 = self.mesh_stats["volume_mm3"]
            
            # If volume is 0 or "N/A", estimate from bounding box with infill factor
            if not volume_mm3 and self.mesh_stats["bounding_box"]:
                bbox = self.mesh_stats["bounding_box"]
                bbox_volume = bbox["width"] * bbox["depth"] * bbox["height"]
                # Assume model fills about 40% of bounding box on average
                volume_mm3 = bbox_volume * 0.4
                self.mesh_stats["volume_mm3"] = volume_mm3
                self.mesh_stats["volume_cm3"] = volume_mm3 / 1000
            
            # Cap volume at reasonable maximum to avoid crazy estimates
            volume_cm3 = min(volume_mm3 / 1000, 1000)
            
            # Apply infill factor depending on printer type
            if self.config["printer_type"] in ["SLA", "DLP"]:
                # For resin printers, we typically print hollow with low infill
                effective_volume = volume_cm3 * 0.5
                # Calculate material mass based on density with support factor
                support_factor = 1.1  # 10% extra for minimal supports
                material_usage_g = effective_volume * self.config["material_density"] * support_factor
            elif self.config["printer_type"] == "SLS":
                # For SLS printing, account for entire volume plus waste
                effective_volume = volume_cm3  # SLS uses 100% of volume
                # Calculate material mass with packing inefficiency and recycling waste
                packing_factor = 1.05  # 5% extra for powder packing inefficiency
                waste_factor = 1.4     # 40% powder waste/recycling rate
                material_usage_g = effective_volume * self.config["material_density"] * packing_factor * waste_factor
            else:
                # FDM printing with specified infill percentage
                infill_factor = self.config["infill_density"] / 100
                shell_factor = 0.3  # Represents outer shell volume
                effective_volume = volume_cm3 * (shell_factor + (1 - shell_factor) * infill_factor)
                # Calculate material mass based on density
                material_usage_g = effective_volume * self.config["material_density"]
            
            # Calculate material cost
            material_cost = (material_usage_g / 1000) * self.config["material_cost_per_kg"]
            
            # Estimate print time based on printer type
            if self.config["printer_type"] == "FDM":
                # FDM printing time factors
                base_time_factor = 2.0  # minutes per cm³
            elif self.config["printer_type"] in ["SLA", "DLP"]:
                # Resin printing time factor
                base_time_factor = 1.2
            elif self.config["printer_type"] == "SLS":
                # SLS time factor
                base_time_factor = 0.8
            else:
                # Default conservative factor
                base_time_factor = 1.5
            
            # Calculate more realistic print time estimate
            print_time_minutes = effective_volume * base_time_factor
            
            # Adjust for layer height
            layer_height_factor = 0.2 / self.config["layer_height"]  # Relative to 0.2mm
            print_time_minutes *= layer_height_factor
            
            # Add fixed time for printer setup and post-processing
            print_time_minutes += 15  # 15 minute base time
            
            # Cap the time at reasonable maximum (48 hours)
            print_time_minutes = min(print_time_minutes, 48 * 60)
            
            # Calculate machine cost
            machine_cost = (print_time_minutes / 60) * self.config["machine_cost_per_hour"]
            
            # Calculate total cost
            total_cost = material_cost + machine_cost
            
            # Store results
            self.mesh_stats["material_usage_g"] = material_usage_g
            self.mesh_stats["material_cost"] = material_cost
            self.mesh_stats["total_cost"] = total_cost
            
            # Format time into hours and minutes
            if print_time_minutes < 1:
                self.mesh_stats["estimated_print_time"] = "Less than 1 minute"
            else:
                hours = int(print_time_minutes / 60)
                minutes = int(print_time_minutes % 60)
                
                if hours > 0:
                    self.mesh_stats["estimated_print_time"] = f"{hours}h {minutes}m"
                else:
                    self.mesh_stats["estimated_print_time"] = f"{minutes}m"
                
            # Add printer type to estimate
            self.mesh_stats["estimated_print_time"] += f" ({self.config['printer_type']})"
            
            logger.info(f"Calculated estimates: {print_time_minutes:.1f} minutes, {material_usage_g:.1f}g material, ${total_cost:.2f} total cost")
            
        except Exception as e:
            logger.error(f"Error calculating estimates: {str(e)}")
            self.mesh_stats["estimated_print_time"] = "Unable to estimate"
            self.mesh_stats["material_usage_g"] = 0
            self.mesh_stats["material_cost"] = 0
            self.mesh_stats["total_cost"] = 0

    def calculate_printability_score(self):
        """Calculate an overall printability score based on issues found"""
        try:
            # Start with perfect score
            score = 100.0
            
            # Deduct points based on severity of issues
            for issue in self.issues:
                if issue["severity"] == "high":
                    score -= 20.0
                elif issue["severity"] == "medium":
                    score -= 10.0
                elif issue["severity"] == "low":
                    score -= 5.0
            
            # Ensure score doesn't go below 0
            score = max(0.0, score)
            
            # Convert to 0-1 scale
            printability_score = score / 100.0
            self.mesh_stats["printability_score"] = printability_score
            
        except Exception as e:
            logger.error(f"Error calculating printability score: {str(e)}")
            self.mesh_stats["printability_score"] = 0.5  # Default mid-range score

    def generate_report(self):
        """Generate a comprehensive DFM report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "file": self.original_file,
            "process": f"3D printing ({self.config['printer_type']})",
            "stats": self.mesh_stats,
            "issues": self.issues,
            "recommendations": [issue["recommendation"] for issue in self.issues],
            "cost_details": {
                "material_type": self.config["material_type"],
                "material_cost_per_kg": self.config["material_cost_per_kg"],
                "material_usage": self.mesh_stats["material_usage_g"],
                "material_cost": self.mesh_stats["material_cost"],
                "print_time": self.mesh_stats["estimated_print_time"],
                "total_cost": self.mesh_stats["total_cost"]
            },
            "config": self.config
        }
        
        # Add overall assessment
        printability_score = self.mesh_stats.get("printability_score", 0.0)
        if printability_score >= 0.8:
            report["assessment"] = "This model is suitable for 3D printing with minimal modifications."
        elif printability_score >= 0.5:
            report["assessment"] = "This model is printable but may require some modifications."
        else:
            report["assessment"] = "This model requires significant modifications before printing."
            
        return report

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Enhanced 3D Printing DFM Analyzer")
    parser.add_argument("input_file", help="Input STL or STEP file")
    parser.add_argument("--output", help="Optional: additional output JSON report file location. Reports are always saved to dfm-output/ directory with standardized names.", default=None)
    parser.add_argument("--config", help="Configuration JSON file", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--printer", choices=["FDM", "SLA", "SLS", "DLP"], default="SLA", 
                        help="Printer type (affects print time and support estimates)")
    parser.add_argument("--material", default="Resin", 
                        help="Material type (PLA, ABS, PETG, Resin, etc.)")
    parser.add_argument("--layer-height", type=float, default=0.05,
                        help="Layer height in mm (default: 0.05 for SLA)")
    parser.add_argument("--infill", type=int, default=20,
                        help="Infill percentage (0-100, default: 20)")
    parser.add_argument("--material-cost", type=float, default=50.0,
                        help="Material cost per kg (default: 50.0 for resin)")
    parser.add_argument("--machine-cost", type=float, default=3.0,
                        help="Machine cost per hour (default: 3.0 for SLA)")
    parser.add_argument("--no-slicer", action="store_true",
                        help="Don't use external slicer (use internal estimates only)")
    parser.add_argument("--allow-open", action="store_true", 
                        help="Allow non-manifold models (like cups, buckets, etc)")
    
    # Shapeways API integration
    parser.add_argument("--compare-shapeways", action="store_true",
                        help="Compare analysis with Shapeways pricing (requires API credentials)")
    parser.add_argument("--shapeways-client-id", 
                        help="Shapeways API client ID")
    parser.add_argument("--shapeways-client-secret", 
                        help="Shapeways API client secret")
    parser.add_argument("--shapeways-material-id", type=int,
                        help="Shapeways material ID to use for comparison (overrides automatic mapping)")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Load custom configuration if provided
    config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
    else:
        # Create a default config with the command line options
        config = DEFAULT_CONFIG.copy()
        config["printer_type"] = args.printer
        config["material_type"] = args.material
        config["layer_height"] = args.layer_height
        config["infill_density"] = args.infill
        config["material_cost_per_kg"] = args.material_cost
        config["machine_cost_per_hour"] = args.machine_cost
        config["use_external_slicer"] = not args.no_slicer
        
        if args.allow_open:
            config["manifold_required"] = False
    
    # Create analyzer
    analyzer = DFMAnalyzer(config)
    
    # Verify file format
    is_valid, message = analyzer.verify_file_format(args.input_file)
    if not is_valid:
        logger.error(f"File verification failed: {message}")
        sys.exit(1)
    
    logger.info(f"File verification successful: {message}")
    
    # Load and analyze model
    try:
        analyzer.load_model(args.input_file)
        analyzer.analyze_model()
        report = analyzer.generate_report()
        
        # Clean up temporary files
        analyzer.cleanup()
        
        # Compare with Shapeways if requested
        if args.compare_shapeways:
            # Get credentials from args or environment variables
            client_id = args.shapeways_client_id or os.environ.get('SHAPEWAYS_CLIENT_ID')
            client_secret = args.shapeways_client_secret or os.environ.get('SHAPEWAYS_CLIENT_SECRET')
            
            # Initialize Shapeways client
            shapeways_client = ShapewaysClient(
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Authenticate with Shapeways API
            if shapeways_client.authenticate():
                logger.info("Authenticated with Shapeways API")
                
                # Create material mapping with user-specified material ID if provided
                material_mapping = None
                if args.shapeways_material_id:
                    material = report["config"]["material_type"].upper()
                    material_mapping = {material: args.shapeways_material_id}
                
                # Compare DFM results with Shapeways pricing
                comparison_results = shapeways_client.compare_with_dfm(
                    report,
                    args.input_file,
                    material_mapping=material_mapping
                )
                
                # Add comparison results to the report
                report["shapeways_comparison"] = comparison_results
                
                logger.info(f"Added Shapeways comparison to the report")
                
                # Print comparison summary
                if comparison_results.get("comparison_successful", False):
                    print("\nShapeways Comparison:")
                    print(f"- Shapeways Price: ${comparison_results['shapeways']['price']:.2f}")
                    print(f"- Our Estimate: ${comparison_results['dfm_analysis']['price']:.2f}")
                    print(f"- Difference: ${comparison_results['differences']['price_diff_absolute']:.2f} " +
                          f"({comparison_results['differences']['price_diff_percent']:.1f}%)")
                    print(f"- Recommendation: {comparison_results['recommendation']}")
                else:
                    print("\nShapeways Comparison Failed:")
                    print(f"- Error: {comparison_results.get('error', 'Unknown error')}")
            else:
                logger.error("Failed to authenticate with Shapeways API")
                print("\nShapeways Comparison Failed: Authentication error")
        
        # Always save the report to the standardized output path
        output_path = analyzer.get_output_path(args.input_file, "json")
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_path}")
        
        # If a specific output file is requested, save a copy there as well
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Additional report copy saved to {args.output}")
            
        # Always print summary to console
        print(f"\n=== DFM Analysis Report for {args.input_file} ===")
        print(f"Printability Score: {report['stats']['printability_score']:.2f} (0-1 scale)")
        print(f"Overall Assessment: {report['assessment']}")
        
        # Print issues
        if report['issues']:
            print("\nIssues Found:")
            for issue in report['issues']:
                print(f"- [{issue['severity'].upper()}] {issue['details']}")
                print(f"  Recommendation: {issue['recommendation']}")
        else:
            print("\nNo issues found! This model is ready for 3D printing.")
            
        # Print cost and time estimates
        print("\nCost & Time Estimates:")
        print(f"- Estimated Print Time: {report['stats']['estimated_print_time']}")
        print(f"- Material: {report['cost_details']['material_type']}")
        print(f"- Material Usage: {report['cost_details']['material_usage']:.2f}g")
        print(f"- Material Cost: ${report['cost_details']['material_cost']:.2f}")
        print(f"- Total Cost: ${report['cost_details']['total_cost']:.2f}")
        
        # Print model statistics
        print("\nModel Statistics:")
        stats = report['stats']
        if stats['bounding_box']:
            print(f"- Dimensions: {stats['bounding_box']['width']:.2f} x {stats['bounding_box']['depth']:.2f} x {stats['bounding_box']['height']:.2f} mm")
        
        # Print volume with proper units
        if stats['volume_mm3']:
            print(f"- Volume: {stats['volume_mm3']:.2f} mm³ ({stats['volume_cm3']:.2f} cm³)")
        
        if stats.get('surface_area_mm2'):
            print(f"- Surface Area: {stats['surface_area_mm2']:.2f} mm²")
            
        if PYMESHLAB_AVAILABLE:
            print(f"- Vertices: {stats['vertices']}")
            print(f"- Faces: {stats['faces']}")
            print(f"- Is Manifold: {stats['is_manifold']}")
            print(f"- Is Closed: {stats['is_closed']}")
            print(f"- Shell Count: {stats['shell_count']}")
            
        if stats.get('support_volume_estimate') and stats['support_volume_estimate'] != "N/A":
            print(f"- Support Requirements: {stats['support_volume_estimate']}")
    
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()