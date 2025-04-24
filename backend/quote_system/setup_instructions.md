# Setup Instructions: Manufacturing Quote System

This guide explains how to set up the development environment and install dependencies for the Manufacturing Quote System.

**Current Date:** Tuesday, April 8, 2025

## 1. Prerequisites

* **Git:** To clone the repository. ([https://git-scm.com/](https://git-scm.com/))
* **Python:** Version 3.9 or higher recommended. ([https://www.python.org/](https://www.python.org/))
    * Ensure Python and `pip` (Python package installer) are added to your system's PATH during installation.
* **C++ Compiler:** Required by some dependencies (`pymeshlab`, potentially `pythonocc-core` if installed via pip).
    * **Linux:** Usually available via `build-essential` (Debian/Ubuntu) or `base-devel` (Arch/Manjaro/EndeavourOS).
    * **macOS:** Install Xcode Command Line Tools: `xcode-select --install`
    * **Windows:** Install Microsoft C++ Build Tools ([https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)).
* **PrusaSlicer:** (Required for accurate 3D Print quoting) Download and install the latest version for your OS from [https://www.prusa3d.com/prusaslicer/](https://www.prusa3d.com/prusaslicer/). The application needs to be able to find the `prusa-slicer` (or `prusa-slicer-console`) executable.

## 2. Clone the Repository

```bash
git clone <your-repository-url>
cd manufacturing_quote_system
```
## 3. Set Up a Virtual Environment (Highly Recommended)
Using a virtual environment prevents conflicts between project dependencies.

### Using `venv` (standard Python):

```bash
# Create the environment (replace .venv with your preferred name)
python -m venv .venv

# Activate the environment:
# Linux / macOS (bash/zsh)
source .venv/bin/activate
# Windows (Command Prompt)
# .venv\Scripts\activate.bat
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### Using `conda` (Recommended if installing pythonocc-core):

```bash
# Create the environment with Python and pip
conda create --name quote-env python=3.12 pip -y

# Activate the environment
conda activate quote-env
```
## 4. Install Dependencies
### 4.1. pythonocc-core (STEP File Support)
This is often the most challenging dependency.

**Method A: Using Conda (Recommended)**
If you are using a Conda environment, this is the easiest way:

```bash
conda install -c conda-forge pythonocc-core -y
```

**Method B: Using Pip (May Require Manual Setup)**
If using `pip` (with `venv` or globally), installation might fail if the underlying OpenCASCADE Technology (OCCT) libraries are not found.

```bash
pip install pythonocc-core
```
If the `pip install` fails, you might need to install OCCT development libraries first:

*   **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install -y libocct*-dev` (package names might vary slightly)
*   **Arch / EndeavourOS:** `sudo pacman -Syu occt`
*   **macOS:** `brew install occt`
*   **Windows:** This is difficult with pip. Conda is strongly recommended. If you must use pip, you might need to manually download OCCT libraries and configure environment variables, which is beyond this basic setup guide.

### 4.2. Install Remaining Python Packages
Once `pythonocc-core` is handled (or if using Conda which installed it), install the rest from `requirements.txt`:

```bash
pip install -r requirements.txt
```
This will install FastAPI, Typer, Trimesh, PyMeshLab, PyVista, PyQt6, etc.

## 5. Configure PrusaSlicer Path (If Needed)
The application will try to automatically find your PrusaSlicer installation. If it fails, or you want to specify a particular version/location:

1.  Find the path to your `prusa-slicer` or `prusa-slicer-console` executable.
    *   **Linux:** Often `/usr/bin/prusa-slicer` or `/home/user/Applications/.../prusa-slicer` (if AppImage).
    *   **macOS:** Typically `/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer`.
    *   **Windows:** Look in `C:\Program Files\Prusa3D\PrusaSlicer\` or `C:\Program Files\PrusaSlicer\`. Use the `prusa-slicer-console.exe` path. Remember to handle spaces if necessary (e.g., using quotes in the `.env` file).
2.  Set the `PRUSA_SLICER_PATH` environment variable or add/modify it in your `.env` file (see next step).

## 6. Configure Application Settings (`.env`)
Copy the example environment file:
```bash
cp .env.example .env
```
Edit the `.env` file using a text editor:
*   Set `MARKUP_FACTOR` to your desired markup (e.g., 1.7 for 70% markup).
*   **Optional:** Set `PRUSA_SLICER_PATH=/path/to/your/prusa-slicer-executable` if auto-detection doesn't work.
*   **Optional:** Add your `GEMINI_API_KEY` or `OPENAI_API_KEY` if you plan to use the (optional) LLM features.
*   **Optional:** Change `LOG_LEVEL` (e.g., to `DEBUG` for more detailed logs).

## 7. Running the Application
Make sure your virtual environment is activated!

### 7.1. Running the API Server
```bash
uvicorn main_api:app --reload --host 0.0.0.0 --port 8000
```
*   `--reload`: Automatically restarts the server when code changes (for development).
*   `--host 0.0.0.0`: Makes the server accessible from other devices on your network.
*   `--port 8000`: Specifies the port number.

Access the API docs (Swagger UI) at `http://localhost:8000/docs`.

### 7.2. Running the CLI Tool
Use the `python main_cli.py` command followed by subcommands and arguments.

```bash
# Show help message
python main_cli.py --help

# List available materials for 3D Printing
python main_cli.py list-materials "3D Printing"

# List available materials for CNC
python main_cli.py list-materials "CNC Machining"

# Get a quote for an STL file using 3D Printing (SLA)
python main_cli.py quote path/to/your/model.stl "3D Printing" sla_resin_standard

# Get a quote for a STEP file using CNC (Aluminum) and save output
python main_cli.py quote path/to/your/part.step "CNC Machining" aluminum_6061 --output output/quote.json

# Get a quote for FDM PLA with visualization and custom markup
python main_cli.py quote path/to/another.stl "3D Printing" fdm_pla_standard --markup 1.8 --visualize
```

## 8. OS-Specific Notes Summary
*   **Arch / EndeavourOS:**
    *   Use `sudo pacman -Syu python python-pip git base-devel occt` for prerequisites.
    *   Consider using `conda` for easier `pythonocc-core` installation.
*   **macOS:**
    *   Use `brew install python git occt` for prerequisites.
    *   Install Xcode Command Line Tools (`xcode-select --install`).
    *   Consider using `conda` for `pythonocc-core`.
*   **Windows:**
    *   Install Python from python.org (ensure Add to PATH is checked).
    *   Install Git from git-scm.com.
    *   Install Microsoft C++ Build Tools.
    *   **Strongly recommend** using Conda for managing the environment, especially `pythonocc-core`.
    *   Be mindful of file paths and potential issues with spaces or backslashes when setting `PRUSA_SLICER_PATH`.

You are now ready to run the DFM analysis and quoting system! 