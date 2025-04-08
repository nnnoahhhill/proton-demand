# ProtonDemand Analysis Engine Setup Instructions

This document provides detailed setup instructions for the ProtonDemand Analysis Engine, including dependencies, environment configuration, and troubleshooting steps.

## System Requirements

- **Python**: 3.8 or higher (3.9+ recommended)
- **Operating System**: Linux, macOS, or Windows
- **Additional Software**:
  - PrusaSlicer (for 3D print analysis)
  - Git (for version control)
  - Python development tools (headers and compiler for native extensions)

## External Dependencies

### Required Software

1. **PrusaSlicer**: Required for slicing simulation and print time/material estimates.
   - [Download PrusaSlicer](https://www.prusa3d.com/prusaslicer/)
   - Install according to your operating system's instructions
   - Note the full path to the executable for environment configuration

2. **PyMeshLab Dependencies**: The PyMeshLab package has system dependencies.
   - **Ubuntu/Debian**:
     ```bash
     sudo apt-get update
     sudo apt-get install -y libglu1-mesa-dev libxi-dev libxmu-dev libglu1-mesa
     ```
   - **macOS**:
     ```bash
     brew install mesa
     ```
   - **Windows**: The required libraries are typically bundled with the Python package.

### Python Dependencies

All Python dependencies are listed in `requirements.txt` and will be installed in the setup steps.

## Installation Steps

1. **Clone the Repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd backend/quote_system
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   # Using venv (recommended)
   python -m venv venv
   
   # On Linux/macOS
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   If you encounter issues with PyMeshLab or other packages with native extensions:
   ```bash
   # Install wheel first to help with binary packages
   pip install wheel
   
   # Try to install requirements again
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Edit the `.env` file with your specific configuration:
     - Set `PRUSA_SLICER_PATH` to the full path of your PrusaSlicer executable
     - Adjust other settings as needed

5. **Verify Installation**:
   ```bash
   # Activate your virtual environment if not already active
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   
   # Run a basic test
   python -c "import trimesh; import pymeshlab; print('Libraries loaded successfully')"
   ```

## Running the System

### API Server

To run the FastAPI server for analysis endpoints:

```bash
# Activate your virtual environment if not already active
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Run the server in development mode (with auto-reload)
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# For production (no auto-reload)
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Command Line Interface

For command-line usage (if implemented):

```bash
# Activate your virtual environment
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Run the CLI with a file to analyze
python main_cli.py analyze --file path/to/model.stl --process print_3d --technology FDM --material PLA-Generic
```

## Testing

Run the tests to ensure everything is working correctly:

```bash
# Activate your virtual environment
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Run all tests
pytest

# Run specific test file
pytest testing/test_3d_print_dfm.py

# Generate test coverage report
pytest --cov=. --cov-report=html
```

Test models are located in `testing/benchmark_models/`. You can generate additional test models with:

```bash
python testing/generate_test_models.py
```

## Troubleshooting

### Common Issues

1. **PrusaSlicer Not Found**:
   - Ensure PrusaSlicer is installed
   - Verify the path in your `.env` file is correct
   - Test the slicer directly:
     ```bash
     # Replace with your actual path
     /path/to/prusa-slicer --help
     ```

2. **PyMeshLab Installation Failures**:
   - Ensure you have the required system dependencies installed (see External Dependencies)
   - Try installing PyMeshLab separately:
     ```bash
     pip install pymeshlab
     ```
   - Check if there are prebuilt wheels for your system on PyPI

3. **Import Errors**:
   - Verify your virtual environment is activated
   - Check if all dependencies are installed:
     ```bash
     pip list
     ```
   - Try reinstalling the problematic package

4. **Permission Issues**:
   - Ensure you have write permissions to the directories
   - For temporary file access errors, check your system's temporary directory permissions

### Logging

The application uses Python's logging system. To increase logging for troubleshooting:

1. Set the `LOG_LEVEL` environment variable in your `.env` file:
   ```
   LOG_LEVEL=DEBUG
   ```

2. Check logs for detailed error information when problems occur

## Additional Resources

- [PrusaSlicer Documentation](https://help.prusa3d.com/en/article/prusaslicer-2-x_2197)
- [PyMeshLab Documentation](https://pymeshlab.readthedocs.io/)
- [Trimesh Documentation](https://trimsh.org/index.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Support

If you encounter issues not covered in this guide, please contact the development team or file an issue in the project repository. 