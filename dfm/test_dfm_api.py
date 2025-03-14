#!/usr/bin/env python3
"""
Test script for Manufacturing DFM API

This script performs basic tests on the DFM API endpoints
to ensure they're functioning correctly.

Usage:
    python test_dfm_api.py
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# API base URL - change this if deployed elsewhere
API_BASE_URL = "http://localhost:8000"
TEST_FILES_DIR = "./test-models"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    url = f"{API_BASE_URL}/health"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "ok":
            print("✅ Health endpoint test passed")
            return True
        else:
            print("❌ Health endpoint test failed - incorrect status")
            return False
    except Exception as e:
        print(f"❌ Health endpoint test failed: {str(e)}")
        return False

def test_materials_endpoint():
    """Test the materials endpoint"""
    print("Testing materials endpoint...")
    
    # Test 3D printing materials
    url = f"{API_BASE_URL}/api/materials?manufacturing_method=3d_printing"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "materials" in data and len(data["materials"]) > 0:
            print("✅ 3D printing materials endpoint test passed")
        else:
            print("❌ 3D printing materials endpoint test failed - no materials returned")
            return False
    except Exception as e:
        print(f"❌ 3D printing materials endpoint test failed: {str(e)}")
        return False
    
    # Test CNC machining materials
    url = f"{API_BASE_URL}/api/materials?manufacturing_method=cnc_machining"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "materials" in data and len(data["materials"]) > 0:
            print("✅ CNC machining materials endpoint test passed")
            return True
        else:
            print("❌ CNC machining materials endpoint test failed - no materials returned")
            return False
    except Exception as e:
        print(f"❌ CNC machining materials endpoint test failed: {str(e)}")
        return False

def test_analyze_endpoint():
    """Test the analyze endpoint with a sample file"""
    print("Testing analyze endpoint...")
    
    # Find a test STL file
    test_files = list(Path(TEST_FILES_DIR).glob("*.stl"))
    if not test_files:
        print("❌ No test STL files found in sample_models directory")
        return False
    
    test_file = test_files[0]
    print(f"Using test file: {test_file}")
    
    url = f"{API_BASE_URL}/api/analyze"
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            data = {
                "manufacturing_method": "auto_select",
                "material": "",
                "tolerance": "standard",
                "finish": "standard",
                "quantity": "1",
                "detailed": "false"
            }
            
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            
            if "analysis_id" in result and "basic_price" in result:
                print(f"✅ Analyze endpoint test passed - ID: {result['analysis_id']}, Price: ${result['basic_price']:.2f}")
                
                # Test status endpoint
                time.sleep(1)  # Wait for processing
                status_url = f"{API_BASE_URL}/api/analyze/{result['analysis_id']}/status"
                status_response = requests.get(status_url)
                
                if status_response.status_code == 200:
                    print(f"✅ Status endpoint test passed")
                    return True
                else:
                    print(f"❌ Status endpoint test failed: {status_response.status_code}")
                    return False
            else:
                print("❌ Analyze endpoint test failed - missing expected fields in response")
                return False
    except Exception as e:
        print(f"❌ Analyze endpoint test failed: {str(e)}")
        return False

def test_recommendation_endpoint():
    """Test the recommendation endpoint"""
    print("Testing recommendation endpoint...")
    
    # Find a test STL file
    test_files = list(Path(TEST_FILES_DIR).glob("*.stl"))
    if not test_files:
        print("❌ No test STL files found in sample_models directory")
        return False
    
    test_file = test_files[0]
    
    url = f"{API_BASE_URL}/api/recommend"
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            
            response = requests.post(url, files=files)
            response.raise_for_status()
            result = response.json()
            
            if "best_method" in result and "confidence" in result:
                print(f"✅ Recommendation endpoint test passed - Best method: {result['best_method']}")
                return True
            else:
                print("❌ Recommendation endpoint test failed - missing expected fields in response")
                return False
    except Exception as e:
        print(f"❌ Recommendation endpoint test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all API tests"""
    print("=== Manufacturing DFM API Tests ===")
    print(f"Testing API at: {API_BASE_URL}")
    print("")
    
    # Run tests
    tests = [
        test_health_endpoint,
        test_materials_endpoint,
        test_analyze_endpoint,
        test_recommendation_endpoint
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print("")
    
    # Print summary
    print(f"Test Summary: {passed}/{len(tests)} tests passed")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)