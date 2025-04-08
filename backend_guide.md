# Backend Setup and Testing Guide

This guide provides comprehensive instructions for setting up and testing the quote generator backend.

## Prerequisites

Before running the backend, ensure you have the following installed:

1. **Python 3.8+**
2. **PrusaSlicer** - Required for accurate 3D printing time and cost estimation
3. **Required Python packages** - See the environment setup section

## Environment Setup

### 1. Install Required Python Packages

```bash
# Using pip
pip install fastapi uvicorn pydantic python-multipart numpy trimesh python-dotenv pymeshlab

# Or using conda
conda install -c conda-forge fastapi uvicorn pydantic python-multipart numpy trimesh python-dotenv pymeshlab
```

### 2. Verify PrusaSlicer Installation

PrusaSlicer is required for accurate 3D printing time and cost estimation. Run the following script to verify and fix your PrusaSlicer installation:

```bash
python fix_prusa_slicer.py
```

This script will:
- Find PrusaSlicer in common locations
- Fix permissions if needed
- Update your `.env` file with the correct path
- Test if PrusaSlicer is working correctly

### 3. Test Your Environment

Run the environment test script to verify that all components are set up correctly:

```bash
python test_dfm_environment.py
```

This script will check:
- If PrusaSlicer is installed and executable
- If the DFM analyzer can find and use PrusaSlicer
- If the environment variables are set correctly

## Running the Backend

### 1. Start the Backend Server

```bash
python dfm/manufacturing_dfm_api.py
```

The server will start on `http://localhost:8000`.

### 2. Test the API

Run the API test script to verify that the quote API is working correctly:

```bash
python test_quote_api.py
```

This script will:
- Test the health endpoint
- Find or create a sample STL model
- Test the quote endpoint with the sample model

## Troubleshooting

### PrusaSlicer Not Found

If you see the error "PrusaSlicer executable not found or not executable", try the following:

1. Run the fix script:
   ```bash
   python fix_prusa_slicer.py
   ```

2. Manually update your `.env` file with the correct path:
   ```
   PRUSA_SLICER_PATH=/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer
   ```

3. Verify the path is correct:
   ```bash
   ls -la /Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer
   ```

4. Make sure the file is executable:
   ```bash
   chmod +x /Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer
   ```

### API Returns "Part cannot be manufactured due to DFM issues"

This error occurs when the DFM analyzer determines that the part has manufacturability issues. To fix this:

1. Check the backend logs for specific issues
2. Try a different model that is more suitable for 3D printing
3. Modify the DFM analyzer thresholds in `dfm/3d-print-dfm-analyzer.py`:
   ```python
   # Increase the printability threshold to be more lenient
   "printability_threshold": 0.6,  # Lower value = more lenient (default is 0.8)
   ```

### Module Import Errors

If you see errors like "No module named 'dfm'" or "No module named 'dotenv'", make sure:

1. You've installed all required packages:
   ```bash
   pip install python-dotenv
   ```

2. Your Python environment is activated:
   ```bash
   conda activate dfm-env  # If using conda
   ```

## Advanced Configuration

### Customizing DFM Analysis Parameters

You can customize the DFM analysis parameters by modifying the `DEFAULT_CONFIG` in `dfm/3d-print-dfm-analyzer.py`:

```python
DEFAULT_CONFIG = {
    # Dimensional constraints
    "min_thickness": 0.8,  # mm - minimum wall thickness
    "min_hole_diameter": 1.0,  # mm - minimum hole diameter
    
    # Thresholds
    "printability_threshold": 0.8,  # 0-1 scale of printability score
    
    # Material and printer settings
    "printer_type": "SLA",  # FDM, SLA, SLS
    "material_type": "Resin",  # PLA, ABS, PETG, Resin, etc.
}
```

### Adding Support for Additional File Formats

The system currently supports STL and STEP files. To add support for additional formats:

1. Modify the `ALLOWED_EXTENSIONS` in `dfm/manufacturing_dfm_api.py`
2. Add conversion logic in the DFM analyzer

## API Documentation

Once the server is running, you can access the API documentation at:

```
http://localhost:8000/docs
```

This provides interactive documentation for all available endpoints.
