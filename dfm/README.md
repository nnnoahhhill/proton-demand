# Manufacturing DFM Analysis System

This system provides Design for Manufacturing (DFM) analysis for multiple manufacturing methods. It currently supports:

- 3D Printing (SLA, FDM, SLS)
- CNC Machining

## Overview

The Manufacturing DFM Analysis System helps engineers and designers analyze 3D models for manufacturability, estimate production costs, and get feedback on design improvements. It integrates several specialized modules to provide a unified API for assessing designs across different manufacturing technologies.

## Components

The system consists of the following components:

1. **3D Print DFM Analyzer** - `/dfm/3d-print-dfm-analyzer.py`
   - Analyzes models for 3D printing
   - Supports SLA, FDM, and SLS technologies
   - Provides printability assessment and cost estimation

2. **CNC Analysis Suite**
   - **Feature Extraction** - `/dfm/cnc-feature-extraction.py`
     - Recognizes machining features (holes, pockets, etc.)
     - Recommends machining strategies
   - **Quoting System** - `/dfm/cnc-quoting-system.py`
     - Cost estimation based on material and machining time
     - Manufacturability assessment for CNC

3. **Unified API** - `/dfm/manufacturing-dfm-api.py`
   - FastAPI-based web API
   - Integrates all analysis components
   - Provides common interface for all manufacturing methods

## Installation

### Prerequisites

- Python 3.8+
- Trimesh
- NumPy
- FastAPI
- Uvicorn
- PyMeshLab (optional, for advanced mesh analysis)
- Open CASCADE (optional, for STEP file support)

### External Dependencies

- PrusaSlicer (for accurate 3D printing time and cost estimation)
  - The system will search for PrusaSlicer in common installation locations
  - You can specify a custom path in the configuration

### Setup

1. Install dependencies from the project root:

```bash
# From the project root directory
pip install -r requirements.txt
```

2. Run the API server:

```bash
# From the project root directory
python -m dfm.manufacturing_dfm_api
```

The API will be available at http://localhost:8000. API documentation is automatically generated and available at http://localhost:8000/docs.

### Alternative Installation with conda

If you prefer using conda, especially for the more complex dependencies:

```bash
# Create and activate conda environment
conda create -n protogo-env python=3.10 numpy pymeshlab
conda activate protogo-env

# Install the rest with pip
pip install -r requirements.txt

# Run the API
python -m dfm.manufacturing_dfm_api
```

## Usage

### API Endpoints

- `GET /health` - API health check
- `POST /api/analyze` - Analyze a 3D model (STL/STEP)
- `GET /api/analyze/{analysis_id}` - Get detailed analysis results
- `GET /api/analyze/{analysis_id}/status` - Check analysis status
- `POST /api/recommend` - Get manufacturing method recommendations
- `GET /api/materials` - List available materials

### Example: Analyzing a Model

```python
import requests

url = "http://localhost:8000/api/analyze"
files = {"file": open("model.stl", "rb")}
data = {
    "manufacturing_method": "auto_select",
    "material": "",
    "tolerance": "standard",
    "finish": "standard",
    "quantity": "1",
    "detailed": "false"
}

response = requests.post(url, files=files, data=data)
result = response.json()
print(f"Analysis ID: {result['analysis_id']}")
print(f"Estimated Cost: ${result['basic_price']:.2f}")
```

### Testing

Run the test suite to verify the API functionality:

```bash
python test_dfm_api.py
```

## File Format Support

- **STL** - Supported for both 3D printing and CNC analysis
- **STEP** - Supported for CNC analysis with Open CASCADE
- Additional formats like OBJ and 3MF may work but are not fully supported

## API Documentation

### OpenAPI Specification

The API automatically provides an OpenAPI specification that can be used for code generation, documentation, and integration. You can access it in multiple ways:

1. **Interactive Documentation**: When the server is running, visit http://localhost:8000/docs for the Swagger UI or http://localhost:8000/redoc for ReDoc.

2. **Raw Specification**: Access the raw OpenAPI specification at http://localhost:8000/openapi.json while the server is running.

3. **Generate Static Files**: Run the included script to generate static specification files:

```bash
# From the project root
python -m dfm.generate_openapi_spec
```

This will create both JSON and YAML versions of the specification in the dfm directory.

### Using the Specification

The OpenAPI specification can be used with various tools:

- **API Clients**: Import into Postman, Insomnia, or similar tools
- **Code Generation**: Generate client libraries using tools like OpenAPI Generator
- **Documentation**: Generate comprehensive documentation using tools like ReDoc
- **SDK Integration**: Integrate with SDKs for various programming languages

## Integration Plan

Refer to `dfm-integration-plan.md` for the roadmap and progress tracking.

## License

This project is proprietary and confidential.