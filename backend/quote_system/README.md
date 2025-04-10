# Backend Quote System README

## 1. Project Goal & Vision

The primary goal of this project is to create a **fast, accurate, and reliable** backend system for generating instant quotes for custom parts manufactured via:

* **3D Printing** (FDM, SLA, SLS)
* **CNC Machining** (3/4/5-Axis)
* **Sheet Metal Processing**

This system includes integrated **Design for Manufacturing (DFM)** analysis to validate geometry and provide feedback before quoting. It aims to replace potentially slow, overly complex, or unreliable existing solutions by focusing on core accuracy, performance (< 10 seconds for DFM), and maintainability through a modular architecture.

The system provides both a **RESTful API** (using FastAPI) for integration with web frontends and other services, and a **Command-Line Interface (CLI)** (using Typer) for local development, testing, and direct use.

## 2. Current Status & Implementation Details

This project is under active development. Here's the status of each major component:

### 2.1. Overall System
* **Architecture:** Modular Python codebase with clear separation between core utilities, process-specific logic, API/CLI interfaces, and visualization.
* **Interfaces:** Functional FastAPI server (`main_api.py`) and Typer CLI (`main_cli.py`) are implemented.
* **Geometry:** Supports loading `.stl` and `.step`/`.stp` files. STEP files are converted to STL internally using `pythonocc-core`. Basic mesh properties (volume, bounds, area) calculated using `Trimesh`.
* **Configuration:** Managed via `.env` file and Pydantic settings (`config.py`), controlling markup, optional tool paths, and API keys.
* **Costing Model:** Follows a simplified model as requested:
    * `Base Cost = Material Cost` (Calculated from volume/weight and material price)
    * `Customer Price = Base Cost * Markup Factor` (Markup factor is configurable)
    * Process time is estimated and reported but **not** included in the `Base Cost`.
* **Testing:** Basic framework using `pytest` is set up (`testing/`). Includes programmatic generation of test models (`testing/generate_test_models.py`) and initial DFM tests for 3D printing (`testing/test_3d_print_dfm.py`). Quote tests are placeholders.

### 2.2. 3D Printing (FDM, SLA, SLS)
* **Status:** Core functionality implemented. Considered the most complete module currently.
* **DFM Analysis:** Implemented using `PyMeshLab` and `Trimesh`. Includes checks for:
    * Build Volume (`dfm_rules.check_bounding_box`)
    * Mesh Integrity (Non-manifold, Holes, Self-intersection basic checks) (`dfm_rules.check_mesh_integrity`)
    * Multiple Disconnected Shells (Configurable, currently CRITICAL fail) (`dfm_rules.check_mesh_integrity`)
    * Overhang Analysis (Warn/Error based on angle) (`dfm_rules.check_overhangs_and_support`)
    * Warping Risk (Basic check for large flat areas near base) (`dfm_rules.check_warping_risk`)
    * Internal Voids / Escape Holes (Basic check for SLA/SLS) (`dfm_rules.check_internal_voids_and_escape`)
    * **Limitation:** `check_thin_walls` currently contains **placeholder logic**. A robust implementation using PyMeshLab filters or other methods is required for accurate thin wall detection.
* **Cost & Time Estimation:**
    * Relies **heavily** on an external slicer (**PrusaSlicer** or compatible) being installed and accessible. The `slicer.py` module handles finding and running the slicer CLI.
    * Uses slicer output (G-code comments) to get accurate print time and material consumption (including implicit support material).
    * Calculates material cost based on slicer's material usage and configured material prices (`processes/print_3d/materials.json`).
    * **Limitation:** Accuracy is dependent on the quality and configuration of the slicer profiles used (currently uses generic defaults). Explicit support material volume/cost is not separated from the main material estimate.

### 2.3. CNC Machining
* **Status:** **Placeholder Implementation Only.** Provides basic structure but is **not accurate** for real-world quoting.
* **DFM Analysis:** Includes very basic checks:
    * Build Volume (`dfm_rules.check_cnc_bounding_box`)
    * Placeholder/basic checks for thin features and tool access/corners (`dfm_rules.check_cnc_thin_features`, `dfm_rules.check_tool_access_and_corners`). These **do not** perform detailed geometric analysis.
* **Cost & Time Estimation:**
    * **Cost:** Placeholder calculates material cost based on *mesh volume* times a fixed *waste factor* times material price. This is **highly inaccurate** as it doesn't account for stock size or features.
    * **Time:** Placeholder calculates time based on *bounding box volume* times a fixed factor plus setup time. This is **highly inaccurate** and doesn't reflect actual machining operations.
* **Needed Implementation:** Requires significant development, including: geometric feature recognition (pockets, holes, bosses), tool accessibility analysis, undercut detection (for 3/5-axis), internal corner radii checks, calculation of machining time based on features/toolpaths/material, and more sophisticated stock material estimation.

### 2.4. Sheet Metal
* **Status:** **Not Implemented.** Directory structure exists (`processes/sheet_metal/`) but contains no functional code.
* **Needed Implementation:** Requires logic for unfolding (flat pattern generation), bend analysis (radius, k-factor, collisions), tooling checks, feature validation (e.g., distance to bends), and cost/time estimation based on cutting, bending, and material usage.

## 3. Architecture

The system uses a modular architecture:

* **`core/`:** Contains shared components like Pydantic data types (`common_types.py`), geometry loading/conversion (`geometry.py`), custom exceptions (`exceptions.py`), and utilities (`utils.py`).
* **`processes/`:** Holds subdirectories for each manufacturing process (e.g., `print_3d/`, `cnc/`). Each process has:
    * A `processor.py` inheriting from `base_processor.py`.
    * `dfm_rules.py` containing specific validation checks.
    * `materials.json` defining material properties.
    * Specific helpers (like `slicer.py` for 3D printing).
* **`main_api.py` / `main_cli.py`:** Entry points for the FastAPI web server and Typer command-line interface, respectively. They orchestrate calls to the appropriate processor.
* **`config.py` / `.env`:** Handles application configuration (markup, paths, keys).
* **`visualization/`:** Contains the `PyVista`-based local 3D viewer (`viewer.py`).
* **`testing/`:** Contains `pytest` tests, fixtures (`conftest.py`), benchmark models, and model generation scripts.

## 4. Key Technologies

* **Python 3.9+:** Core programming language.
* **FastAPI:** High-performance web framework for the API.
* **Typer:** Modern CLI framework based on Click.
* **Pydantic:** Data validation and settings management.
* **Trimesh:** Loading meshes (STL), basic geometry analysis and manipulation.
* **pythonocc-core:** Reading and processing STEP files (CAD format).
* **PyMeshLab:** Advanced mesh analysis (wrapping MeshLab), used for robust DFM checks.
* **PrusaSlicer (External):** Used via CLI for accurate 3D print time/material estimation. Dependency must be installed separately.
* **PyVista & PyQt6/PySide6:** For 3D visualization in the local CLI tool.
* **Rich:** For enhanced console output in the CLI.
* **pytest:** For automated testing.

## 5. Features

* **Multi-Process Support:** Designed for 3D Printing, CNC, and Sheet Metal (though only 3DP is substantially implemented).
* **File Support:** Accepts `.stl` and `.step`/`.stp` files.
* **DFM Analysis:** Provides Pass/Warning/Fail status with detailed issues, recommendations, and severity levels.
* **Simplified Costing:** Calculates material cost accurately (based on slicer for 3DP, placeholder for CNC) and applies a configurable markup for customer pricing.
* **Time Estimation:** Provides process time estimates (accurate for 3DP via slicer, placeholder for CNC).
* **REST API:** Offers `/quote`, `/materials/{process}`, `/health` endpoints. Auto-generated documentation at `/docs`.
* **CLI Tool:** Provides `quote` and `list-materials` commands for local use.
* **Visualization:** Optional `--visualize` flag in the CLI launches an interactive 3D viewer highlighting DFM issues (requires GUI environment).

## 6. Limitations & Known Issues

* **Performance Target:** While DFM checks aim for < 10 seconds, **3D Print quotes involving the external slicer will often exceed this target**, especially for complex models. CNC/Sheet Metal estimates (when geometry-based) are expected to be faster.
* **Slicer Dependency (3DP):** Accurate 3D print quotes **require PrusaSlicer** (or a compatible slicer CLI configured) to be installed and findable by the system. If not found or it fails, quoting will fail. This is a significant external dependency.
* **`pythonocc-core` Installation:** Can be difficult to install via `pip` across different platforms due to its C++ dependencies. Using `conda` is strongly recommended. See `setup_instructions.md`.
* **3DP DFM Accuracy:**
    * The crucial **Thin Wall check** (`dfm_rules.check_thin_walls`) is currently a **placeholder** and needs proper implementation for reliable results.
    * Overhang analysis is basic (angle-based) and doesn't guarantee perfect support generation by the slicer.
    * Warping/Void checks are heuristic and may produce false positives/negatives.
* **CNC Accuracy:** DFM checks and **especially cost/time estimates for CNC are currently placeholders and highly inaccurate.** They need complete reimplementation based on proper CNC principles.
* **STEP Conversion:** Conversion from STEP to STL using `pythonocc-core` might lose precision or fail on very complex/problematic STEP files. The quality of the resulting mesh affects subsequent analyses.
* **Units:** The system generally assumes input files use **millimeters (mm)**. Results might be incorrect if files use different units.
* **Error Handling:** While specific exceptions are caught, edge cases in geometry processing or slicer interaction might lead to unexpected errors.
* **Scalability:** The current synchronous API request handling and in-memory state might not scale well under heavy load in a production environment.

## 7. Future Work & Areas for Improvement

* **[CRITICAL] Implement 3DP Thin Wall Check:** Replace the placeholder in `processes/print_3d/dfm_rules.py` with a robust thickness analysis method (e.g., using advanced PyMeshLab filters if suitable, or potentially Trimesh ray casting).
* **[MAJOR] Implement CNC DFM & Quoting:** Develop proper feature recognition, tool accessibility analysis, corner/undercut checks, and physics/feature-based time/cost estimation.
* **[MAJOR] Implement Sheet Metal:** Add processor, DFM rules (unfolding, bends), and quoting logic.
* **Enhance 3DP Costing:** Explore options for explicitly calculating support material volume/cost, potentially through more detailed slicer output parsing or geometric approximations.
* **Refine Slicer Integration:** Allow configuration of specific slicer profiles; potentially add support for CuraEngine as an alternative. Handle slicer warnings more effectively.
* **LLM Integration:** Add optional calls to LLMs (Gemini, OpenAI) using configured API keys to generate user-friendly explanations and fixing suggestions based on technical DFM issues.
* **Testing:** Add comprehensive tests for quoting logic (`test_3d_print_quote.py`, `test_cnc.py`), including checks against expected costs/times for benchmark models (based on internal logic, not external sites). Expand DFM test coverage.
* **Visualization:** Improve the PyVista viewer (better legends, more highlight types, potentially saving viewpoints).
* **Configuration:** Move more magic numbers/thresholds from code (e.g., `dfm_rules.py`) into the main configuration (`config.py` or separate config files). Add support for machine profiles.
* **API Scalability:** Investigate asynchronous processing for long-running tasks (slicing, complex DFM) using background tasks or task queues (Celery).
* **Error Reporting:** Improve error messages and potentially provide correlation IDs for easier debugging between API calls and logs.

## 8. Setup

**Prerequisites:**
*   Python 3.9+ installed.
*   `conda` package manager recommended (especially for installing `pythonocc-core`). See [Miniconda Installation](https://docs.conda.io/projects/miniconda/en/latest/).
*   (Optional but needed for 3D Print quoting) **PrusaSlicer** (or compatible fork like SuperSlicer) installed and accessible from the command line.
    *   Verify by running `prusa-slicer --help` (or the equivalent for your slicer) in your terminal.
    *   If not automatically found, set the `PRUSA_SLICER_PATH` environment variable in your `.env` file to the full path of the slicer executable.

**Steps:**

1.  **Clone the repository** (if not already done).
2.  **Navigate to the `backend/quote_system` directory:**
    ```bash
    cd path/to/your/project/backend/quote_system
    ```
3.  **(Recommended) Create and activate a Conda environment:**
    ```bash
    conda create -n quote_env python=3.10 -y
    conda activate quote_env
    ```
    (Replace `quote_env` with your preferred name and `3.10` with your desired Python 3.9+ version).
4.  **Install dependencies:**
    *   **Using Conda (Recommended):** This handles `pythonocc-core` most reliably.
        ```bash
        # Install pythonocc-core first from conda-forge
        conda install -c conda-forge pythonocc-core=7.7.0 -y

        # Install remaining dependencies using pip within the conda environment
        # This includes fastapi, typer, pydantic-settings, trimesh, pymeshlab,
        # manifold3d (for trimesh booleans), pyvista, etc.
        pip install -r requirements.txt
        ```
    *   **Using Pip only (May fail for `pythonocc-core` or `manifold3d` dependencies):**
        ```bash
        pip install -r requirements.txt
        ```
        If `pythonocc-core` fails, try the Conda method. If `manifold3d` installation causes issues, ensure you have necessary build tools installed or check its specific platform requirements.
5.  **Create a `.env` file:**
    *   Copy the example: `cp .env.example .env`
    *   Edit the `.env` file if needed:
        *   Set `PRUSA_SLICER_PATH=/path/to/your/prusa-slicer-console` if the slicer is not in your system's PATH.
        *   Add API keys (e.g., `GEMINI_API_KEY=...`) if you plan to use LLM features (currently not implemented).

## 9. Basic Usage

**Important:** Ensure your Conda environment (e.g., `quote_env`) is activated before running commands:
```bash
conda activate quote_env
```

### Running the API Server

Use `uvicorn` to run the FastAPI server:

```bash
# From the backend/quote_system directory
uvicorn main_api:app --reload
```

*   `--reload`: Automatically restarts the server when code changes (useful for development).
*   The API will typically be available at `http://127.0.0.1:8000`.
*   Access interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.
*   Access alternative API documentation (ReDoc) at `http://127.0.0.1:8000/redoc`.

**API Example (`curl`):**

```bash
curl -X POST "http://127.0.0.1:8000/quote" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "model_file=@/path/to/your/benchmark_models/pass_cube_10mm.stl" \
     -F "process=3D Printing" \
     -F "material_id=sla-resin-standard-clear"
```
(Replace `material_id` and file path as needed)

### Running the CLI Tool

Use `python main_cli.py` followed by the desired command:

```bash
# From the backend/quote_system directory

# List available materials for 3D Printing
python main_cli.py list-materials "3D Printing"

# List available materials for CNC Machining
python main_cli.py list-materials "CNC Machining"

# Get a quote for a 3D Print model (using an SLA material)
python main_cli.py quote ./testing/benchmark_models/pass_cube_10mm.stl "3D Printing" "sla-resin-standard-clear"

# Get a quote for a CNC model (using Aluminum) and save JSON output
python main_cli.py quote ./testing/benchmark_models/pass_cube_10mm.stl "CNC Machining" "cnc-aluminum-6061" -o quote_output.json

# Get a quote and visualize DFM issues (requires PyVista and a GUI)
python main_cli.py quote ./testing/benchmark_models/fail_non_manifold_edge.stl "3D Printing" "sla-resin-standard-clear" --visualize
```

### Running Tests

Ensure `pytest` is installed (`pip install pytest`).

1.  **Generate Benchmark Models:** Before running tests that use the models, generate them:
    ```bash
    # From the backend/quote_system directory
    python testing/generate_test_models.py
    ```
    This will create/update the `.stl` files in `backend/quote_system/testing/benchmark_models/`.

2.  **Run Tests:**
    ```bash
    # From the backend/quote_system directory
    pytest
    ```
    Or run specific test files:
    ```bash
    pytest testing/test_3d_print_dfm.py
    pytest testing/test_3d_print_quote.py
    ```
    *Note:* Some quote tests might be skipped if a required material ID isn't found or if the PrusaSlicer executable cannot be located.

## 10. License
This project is licensed under the MIT License. Please add a LICENSE file containing the MIT License text to the project root.


**Instructions:** Replace the content of your existing `README.md` with this expanded version.

**Rationale:**
* **Structure:** Organized into clear sections (Goal, Status, Architecture, Tech, Features, Limitations, Future Work, Setup, Usage, License).
* **Detail:** Provides much more context on the implementation status of each module, especially highlighting the placeholder nature of CNC and Sheet Metal, and the known limitations of the 3D Printing implementation (thin walls, slicer dependency).
* **Transparency:** Clearly lists known issues, potential failure points (slicer, pythonocc-core), and areas needing significant work.
* **Roadmap:** The "Future Work" section acts as a mini-roadmap for improving the system.
* **Clarity:** Uses formatting (bolding, code blocks, lists) to improve readability.

---

**Updated Directory Structure:**

manufacturing_quote_system/
├── requirements.txt                     
├── main_api.py                          
├── main_cli.py                          
├── .env.example                         
├── config.py                            
├── core/
│   ├── init.py
│   ├── common_types.py                
│   ├── geometry.py                    
│   ├── exceptions.py                  
│   └── utils.py                       
├── processes/
│   ├── init.py
│   ├── base_processor.py              
│   ├── print_3d/
│   │   ├── init.py
│   │   ├── processor.py               
│   │   ├── dfm_rules.py               
│   │   ├── slicer.py                  
│   │   └── materials.json             
│   ├── cnc/
│   │   ├── init.py
│   │   ├── processor.py               
│   │   ├── dfm_rules.py               
│   │   └── materials.json             
│   └── sheet_metal/                   
│       ├── init.py
│       ├── processor.py
│       ├── dfm_rules.py
│       └── materials.json
├── visualization/
│   ├── init.py
│   └── viewer.py                      
├── testing/
│   ├── init.py
│   ├── conftest.py                    
│   ├── test_3d_print_dfm.py           
│   ├── test_3d_print_quote.py         
│   ├── test_cnc.py                    
│   ├── benchmark_models/              
│   │   ├── ...
│   └── generate_test_models.py        
├── setup_instructions.md                
└── README.md                            