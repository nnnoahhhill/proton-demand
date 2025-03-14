#!/usr/bin/env python3
"""
Generate OpenAPI specification for the Manufacturing DFM API

This script generates an OpenAPI specification file from the FastAPI app
without needing to run the server.

Usage:
    python generate_openapi_spec.py
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path to make imports work correctly
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the app from the manufacturing-dfm-api module
from dfm.manufacturing_dfm_api import app  # Note: Replace hyphens with underscores for import

def generate_openapi_spec(output_file="dfm/openapi.json"):
    """Generate an OpenAPI spec JSON file from the FastAPI app"""
    openapi_schema = app.openapi()
    
    # Write the schema to a file
    with open(output_file, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"OpenAPI specification saved to {output_file}")
    
    # Also write a YAML version if PyYAML is available
    try:
        import yaml
        yaml_file = output_file.replace(".json", ".yaml")
        with open(yaml_file, "w") as f:
            yaml.dump(openapi_schema, f, default_flow_style=False)
        print(f"OpenAPI specification also saved as YAML to {yaml_file}")
    except ImportError:
        print("PyYAML not installed. Skipping YAML format generation.")
        print("Install with: pip install pyyaml")

if __name__ == "__main__":
    generate_openapi_spec()