# Proton Demand: On-Demand Manufacturing Price Calculator

Proton Demand is an instant quoting platform for 3D printing, CNC machining, and sheet metal fabrication. This tool provides immediate pricing for manufacturing parts without the traditional markup, eliminating the need for sales calls or lengthy quotation processes.

## Features

- **Instant Quoting**: Upload 3D models (STL/STEP files) and receive immediate pricing
- **Multiple Manufacturing Methods**: Support for 3D printing (FDM, SLA, SLS), CNC machining, and sheet metal fabrication
- **Design for Manufacturing (DFM) Analysis**: Automatic analysis of parts for manufacturability
- **Transparent Pricing**: No hidden fees or markups typical of traditional manufacturing services
- **Fast Turnaround**: Streamlined ordering and production process

## Technology Stack

### Frontend
- Next.js
- React
- Three.js for 3D model visualization
- TailwindCSS for styling
- Stripe for payment processing

### Backend
- FastAPI (Python)
- PrusaSlicer for 3D print simulation and analysis
- PyMeshLab for mesh analysis
- OpenCascade (optional) for STEP file support
- Stripe API integration

## Getting Started

### Prerequisites

- Node.js (v16+)
- Python 3.8+
- PrusaSlicer
- (Optional) OpenCascade for advanced STEP file analysis

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/proton-demand.git
cd proton-demand
```

2. Set up the frontend:
```bash
npm install
```

3. Set up the Python environment:
```bash
# Using conda (recommended)
conda env create -f environment.yml
conda activate dfm-env

# Or using pip
pip install -r requirements.txt
```

4. Configure PrusaSlicer:
```bash
python fix_prusa_slicer.py
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application

1. Start the backend server:
```bash
python dfm/manufacturing_dfm_api.py
```

2. Start the frontend development server:
```bash
npm run dev
```

3. Access the application at http://localhost:3000

## Architecture

The system consists of two main components:

1. **Frontend**: A Next.js application that provides the user interface for uploading models, configuring manufacturing options, and processing payments.

2. **Backend**: A FastAPI application that handles:
   - File uploads and processing
   - DFM (Design for Manufacturing) analysis
   - Price calculation
   - Integration with manufacturing workflows

The backend leverages specialized components:
- **3D Print DFM Analyzer**: Analyzes models for 3D printing compatibility
- **CNC Analysis Suite**: Provides feature extraction and quoting for CNC parts
- **Sheet Metal Analysis**: Evaluates sheet metal designs for manufacturability

## Testing

Run the following commands to test the system:

```bash
# Test the backend environment
python test_environment.py

# Test the DFM analysis system
python test_dfm_environment.py

# Test the quote API
python test_quote_api.py
```

## Deployment

The application is configured for deployment to Vercel. Use the following command to build for production:

```bash
npm run build
```

## License

This project is proprietary and confidential.

## Support

For any questions or support needs, please contact the development team. 