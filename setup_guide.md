# Setup Guide for Quote Generator Backend

This guide provides comprehensive instructions for setting up the environment required for the quote generator backend, with a focus on PrusaSlicer and other critical dependencies.

## Table of Contents

1. [Setting Up the Python Environment](#1-setting-up-the-python-environment)
2. [Installing and Configuring PrusaSlicer](#2-installing-and-configuring-prusaslicer)
3. [Installing OpenCascade (for STEP File Support)](#3-installing-opencascade-for-step-file-support)
4. [Testing Your Environment](#4-testing-your-environment)
5. [Troubleshooting Common Issues](#5-troubleshooting-common-issues)
6. [Verifying the Complete System](#6-verifying-the-complete-system)
7. [Advanced Configuration](#7-advanced-configuration)

## 1. Setting Up the Python Environment

First, let's set up the Python environment with all required packages:

### Option A: Using Conda (Recommended)

Conda provides better management of complex dependencies, especially for packages with binary components like PyMeshLab and OpenCascade.

```bash
# Create and activate the conda environment from the environment.yml file
conda env create -f environment.yml
conda activate dfm-env

# Verify the environment was created successfully
conda list
```

### Option B: Using pip

If you prefer using pip:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Installing and Configuring PrusaSlicer

PrusaSlicer is a critical dependency for accurate 3D printing time and cost estimation. The system is designed to use it directly, with no fallbacks to less accurate methods.

### Installing PrusaSlicer

#### On macOS:
```bash
# Using Homebrew
brew install --cask prusa-slicer
```

#### On Linux:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install prusa-slicer

# Or download the AppImage from PrusaSlicer website
# https://www.prusa3d.com/prusaslicer/
```

#### On Windows:
Download and install from the [PrusaSlicer website](https://www.prusa3d.com/prusaslicer/).

### Verifying PrusaSlicer Installation

```bash
# Check if PrusaSlicer is in your PATH
which prusa-slicer  # On Windows: where prusa-slicer

# Or check the default installation locations
ls /Applications/PrusaSlicer.app/Contents/MacOS/prusa-slicer  # macOS
ls "C:\Program Files\PrusaSlicer\prusa-slicer.exe"  # Windows
```

### Configuring PrusaSlicer Path in Your Application

If PrusaSlicer isn't in your PATH, you'll need to specify its location in your configuration:

1. Create a config file at `dfm/config.json`:

```json
{
  "slicer_path": "/path/to/prusa-slicer",
  "printer_type": "FDM",
  "printer_profiles": {
    "FDM": "Original Prusa i3 MK3S",
    "SLA": "Original Prusa SL1"
  }
}
```

2. Update the path to match your PrusaSlicer installation.

## 3. Installing OpenCascade (for STEP File Support)

OpenCascade is used for advanced STEP file analysis. While it's optional, it provides better feature recognition for CNC machining.

### Using Conda (Easiest Method)

```bash
# If you're using conda, you can install pythonocc-core
conda install -c conda-forge pythonocc-core
```

### Verifying OpenCascade Installation

```python
# Run this Python code to verify OpenCascade is working
import OCC.Core.BRepPrimAPI
print("OpenCascade is installed correctly!")
```

## 4. Testing Your Environment

Now let's verify that everything is set up correctly:

### 1. Run the Environment Test Script

Create a file called `test_environment.py`:

```python
#!/usr/bin/env python3
"""
Test script to verify the environment setup for the DFM analysis system
"""

import sys
import os
import subprocess
import importlib

def check_module(module_name, package_name=None):
    """Check if a Python module is available"""
    if package_name is None:
        package_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name} is installed")
        return True
    except ImportError:
        print(f"❌ {package_name} is NOT installed")
        return False

def check_executable(name, command):
    """Check if an executable is available"""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print(f"✅ {name} is installed and working")
            return True
        else:
            print(f"❌ {name} is installed but returned an error")
            return False
    except FileNotFoundError:
        print(f"❌ {name} is NOT installed or not in PATH")
        return False

def main():
    """Run all environment checks"""
    print("=== Python Environment Check ===")
    print(f"Python version: {sys.version}")
    print("")
    
    print("=== Required Python Packages ===")
    required_modules = [
        ("numpy", "NumPy"),
        ("trimesh", "Trimesh"),
        ("pymeshlab", "PyMeshLab"),
        ("fastapi", "FastAPI"),
    ]
    
    for module, name in required_modules:
        check_module(module, name)
    
    print("")
    print("=== Optional Python Packages ===")
    optional_modules = [
        ("OCC.Core", "pythonocc-core (OpenCascade)"),
        ("open3d", "Open3D"),
    ]
    
    for module, name in optional_modules:
        check_module(module, name)
    
    print("")
    print("=== External Dependencies ===")
    
    # Check PrusaSlicer
    prusa_commands = [
        ["prusa-slicer", "--help"],
        ["/Applications/PrusaSlicer.app/Contents/MacOS/prusa-slicer", "--help"],
        ["C:\\Program Files\\PrusaSlicer\\prusa-slicer.exe", "--help"]
    ]
    
    prusa_found = False
    for cmd in prusa_commands:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                print(f"✅ PrusaSlicer is installed at: {cmd[0]}")
                prusa_found = True
                break
        except FileNotFoundError:
            continue
    
    if not prusa_found:
        print("❌ PrusaSlicer is NOT installed or not found in common locations")
    
    print("")
    print("=== Environment Check Complete ===")

if __name__ == "__main__":
    main()
```

Run the test script:

```bash
python test_environment.py
```

### 2. Test the DFM Analysis API

```bash
# Start the API server
python dfm/manufacturing_dfm_api.py

# In another terminal, run the test script
./test-api-python.sh
```

## 5. Troubleshooting Common Issues

### PrusaSlicer Not Found

If the system can't find PrusaSlicer:

1. Locate your PrusaSlicer executable:
   ```bash
   # On macOS
   find /Applications -name "prusa-slicer"
   
   # On Linux
   which prusa-slicer
   
   # On Windows (PowerShell)
   Get-ChildItem -Path "C:\Program Files" -Recurse -Filter "prusa-slicer.exe"
   ```

2. Create or update the configuration file with the correct path:
   ```json
   {
     "slicer_path": "/path/to/prusa-slicer"
   }
   ```

### PyMeshLab Installation Issues

PyMeshLab can be tricky to install. If you're having issues:

```bash
# Try installing with conda
conda install -c conda-forge pymeshlab

# Or with pip (may require additional system dependencies)
pip install pymeshlab
```

### OpenCascade/pythonocc-core Issues

If you're having trouble with OpenCascade:

```bash
# The easiest way is to use conda
conda install -c conda-forge pythonocc-core

# Verify it works
python -c "import OCC.Core.BRepPrimAPI; print('OpenCascade works!')"
```

## 6. Verifying the Complete System

To verify that the entire system is working correctly:

1. Start the backend:
   ```bash
   python dfm/manufacturing_dfm_api.py
   ```

2. Start the frontend:
   ```bash
   npm run dev
   ```

3. Upload a test model through the frontend interface and check if:
   - The model is analyzed correctly
   - You receive a quote with accurate pricing
   - The system identifies any manufacturability issues

4. Check the backend logs for any errors or warnings:
   ```bash
   # Look for messages about PrusaSlicer or other dependencies
   tail -f backend.log
   ```

## 7. Advanced Configuration

For advanced users, you can fine-tune the system:

### Customizing PrusaSlicer Profiles

1. Open PrusaSlicer and configure your printer profiles
2. Export the configuration:
   ```bash
   # Export the configuration bundle
   prusa-slicer --export-config /path/to/config.ini
   ```

3. Reference this configuration in your application:
   ```json
   {
     "slicer_path": "/path/to/prusa-slicer",
     "slicer_config": "/path/to/config.ini"
   }
   ```

### Enabling Detailed Logging

To get more detailed logs for troubleshooting:

```python
# In dfm/manufacturing_dfm_api.py, change the logging level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

### Creating a Configuration File for the DFM Analyzer

For more advanced configuration, create a comprehensive config file at `dfm/config.json`:

```json
{
  "slicer_path": "/path/to/prusa-slicer",
  "printer_type": "FDM",
  "printer_profiles": {
    "FDM": "Original Prusa i3 MK3S",
    "SLA": "Original Prusa SL1",
    "SLS": "Generic SLS"
  },
  "materials": {
    "FDM": {
      "PLA": {
        "density": 1.24,
        "cost_per_kg": 25.0
      },
      "ABS": {
        "density": 1.04,
        "cost_per_kg": 30.0
      },
      "PETG": {
        "density": 1.27,
        "cost_per_kg": 35.0
      },
      "TPU": {
        "density": 1.21,
        "cost_per_kg": 45.0
      }
    },
    "SLA": {
      "STANDARD_RESIN": {
        "density": 1.1,
        "cost_per_liter": 65.0
      }
    },
    "SLS": {
      "NYLON_12_WHITE": {
        "density": 1.01,
        "cost_per_kg": 80.0
      },
      "NYLON_12_BLACK": {
        "density": 1.01,
        "cost_per_kg": 85.0
      }
    }
  },
  "analysis_settings": {
    "min_wall_thickness": {
      "FDM": 0.8,
      "SLA": 0.5,
      "SLS": 0.8
    },
    "min_feature_size": {
      "FDM": 0.4,
      "SLA": 0.1,
      "SLS": 0.5
    },
    "max_overhang_angle": {
      "FDM": 45,
      "SLA": 30,
      "SLS": 90
    }
  },
  "pricing": {
    "machine_cost_per_hour": {
      "FDM": 5.0,
      "SLA": 8.0,
      "SLS": 15.0
    },
    "setup_fee": 10.0,
    "minimum_order": 25.0,
    "markup_factor": 1.5
  },
  "logging": {
    "level": "INFO",
    "file": "dfm_analyzer.log"
  }
}
```

## Conclusion

By following these steps, you should have a fully functional environment for your quote generator backend. The system is designed to use advanced tools like PrusaSlicer for accurate analysis, with no fallbacks to less accurate methods.

If you encounter any specific issues during setup, please refer to the troubleshooting section or consult the project documentation for more detailed information.
