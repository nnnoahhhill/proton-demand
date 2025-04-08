#!/usr/bin/env python3
"""
Test script for the quote API
"""

import os
import sys
import json
import requests
from pathlib import Path

# Configure basic logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Quote-API-Test')

def test_health_endpoint():
    """Test the health endpoint"""
    logger.info("Testing health endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/health")
        if response.status_code == 200:
            logger.info("✅ Health endpoint is working")
            return True
        else:
            logger.error(f"❌ Health endpoint returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing health endpoint: {str(e)}")
        return False

def test_quote_endpoint(model_file_path):
    """Test the quote endpoint with a sample model"""
    logger.info(f"Testing quote endpoint with model: {model_file_path}")
    
    if not os.path.exists(model_file_path):
        logger.error(f"❌ Model file not found: {model_file_path}")
        return False
    
    try:
        # Prepare the request
        url = "http://localhost:8000/api/getQuote"
        
        # Create the form data
        files = {
            'model_file': (os.path.basename(model_file_path), open(model_file_path, 'rb'), 'application/octet-stream')
        }
        
        data = {
            'process': '3DP_FDM',
            'material': 'pla',
            'finish': 'standard'
        }
        
        # Send the request
        response = requests.post(url, files=files, data=data)
        
        # Check the response
        if response.status_code == 200:
            logger.info("✅ Quote endpoint returned 200 OK")
            
            # Parse the response
            try:
                result = response.json()
                logger.info(f"Quote result: {json.dumps(result, indent=2)}")
                
                # Check if the quote has the expected fields
                if 'price' in result and 'currency' in result:
                    logger.info(f"✅ Quote price: {result['price']} {result['currency']}")
                    return True
                else:
                    logger.error("❌ Quote response is missing price or currency fields")
                    return False
            except Exception as e:
                logger.error(f"❌ Error parsing quote response: {str(e)}")
                return False
        else:
            logger.error(f"❌ Quote endpoint returned status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing quote endpoint: {str(e)}")
        return False

def find_sample_model():
    """Find a sample STL model for testing"""
    # Check common locations for sample models
    test_model_dirs = [
        "test-models",
        "public/test-models",
        "samples",
        "models"
    ]
    
    for dir_path in test_model_dirs:
        if os.path.exists(dir_path):
            # Look for STL files
            for file in os.listdir(dir_path):
                if file.lower().endswith('.stl'):
                    model_path = os.path.join(dir_path, file)
                    logger.info(f"Found sample model: {model_path}")
                    return model_path
    
    # If no model found, create a simple cube
    logger.warning("No sample model found, creating a simple cube")
    
    # Create a directory for the test model
    os.makedirs("test-models", exist_ok=True)
    
    # Path to the cube model
    cube_path = "test-models/cube.stl"
    
    # Check if the cube already exists
    if os.path.exists(cube_path):
        logger.info(f"Using existing cube model: {cube_path}")
        return cube_path
    
    # Create a simple cube STL file
    try:
        import numpy as np
        from stl import mesh
        
        # Define the 8 vertices of the cube
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1]
        ])
        
        # Define the 12 triangles composing the cube
        faces = np.array([
            [0, 3, 1],
            [1, 3, 2],
            [0, 4, 7],
            [0, 7, 3],
            [4, 5, 6],
            [4, 6, 7],
            [5, 1, 2],
            [5, 2, 6],
            [2, 3, 6],
            [3, 7, 6],
            [0, 1, 5],
            [0, 5, 4]
        ])
        
        # Create the mesh
        cube = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                cube.vectors[i][j] = vertices[f[j], :]
        
        # Write the mesh to file
        cube.save(cube_path)
        logger.info(f"Created cube model: {cube_path}")
        return cube_path
    except Exception as e:
        logger.error(f"❌ Error creating cube model: {str(e)}")
        return None

def main():
    """Main function to test the quote API"""
    logger.info("=== Quote API Test ===")
    
    # Test the health endpoint
    if not test_health_endpoint():
        logger.error("❌ Health endpoint test failed. Is the API server running?")
        return
    
    # Find a sample model
    model_path = find_sample_model()
    if not model_path:
        logger.error("❌ Could not find or create a sample model")
        return
    
    # Test the quote endpoint
    test_quote_endpoint(model_path)
    
    logger.info("=== Quote API Test Complete ===")

if __name__ == "__main__":
    main()
