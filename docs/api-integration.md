# API Integration Guide

This document explains how to integrate the Next.js frontend with the Python DFM API backend.

## Overview

The frontend and backend communicate through a REST API. The backend is a Python FastAPI application that provides manufacturing analysis and quoting functionality. The frontend is a Next.js application that presents a user interface for uploading models and viewing quotes.

## Running the Backend

The Python backend needs to be run separately from the Next.js frontend:

```bash
# Activate the conda environment
conda activate dfm-env

# Run the API server from the project root
python -m dfm.manufacturing_dfm_api
```

This will start the FastAPI server on `http://localhost:8000`.

## API Endpoints

### GET /api/getQuote

This endpoint performs DFM analysis and returns a quote if the part can be manufactured.

#### Request

```
POST /api/getQuote
Content-Type: multipart/form-data
```

Parameters:
- `model_file`: 3D model file (.stl, .step, or .stp)
- `process`: Manufacturing process (CNC, 3DP_SLA, 3DP_SLS, 3DP_FDM, SHEET_METAL)
- `material`: Material to use, specific to the selected process
- `finish`: Surface finish quality, specific to the selected process
- `drawing_file`: Optional engineering drawing (.pdf)

#### Successful Response (200 OK)

```json
{
  "success": true,
  "quote_id": "QUOTE-1679345678-1234",
  "price": 235.75,
  "currency": "USD",
  "lead_time_days": 5,
  "manufacturing_details": {
    "process": "CNC",
    "material": "aluminum_6061",
    "finish": "standard",
    "boundingBox": {
      "x": 100,
      "y": 50,
      "z": 25
    },
    "volume": 125000,
    "surfaceArea": 15000
  }
}
```

#### Error Response (400 Bad Request)

```json
{
  "success": false,
  "quote_id": "QUOTE-1679345678-5678",
  "message": "Part cannot be manufactured due to DFM issues",
  "dfm_issues": [
    {
      "type": "thin_wall",
      "severity": "critical",
      "description": "Wall thickness of 0.3mm is below minimum threshold of 0.8mm",
      "location": {
        "x": 10,
        "y": 20,
        "z": 30
      }
    }
  ]
}
```

## Frontend Integration

In the frontend code, use the API service in `lib/api.ts` to communicate with the backend:

```typescript
import { getQuote } from '@/lib/api';

// Example usage in a form submission handler
async function handleSubmit(formData) {
  const response = await getQuote({
    modelFile: formData.modelFile,
    process: formData.process,
    material: formData.material,
    finish: formData.finish,
    drawingFile: formData.drawingFile
  });

  if (response.success) {
    // Display quote information
    console.log(`Quote price: $${response.price}`);
  } else {
    // Handle error or DFM issues
    console.error(`Error: ${response.error || response.message}`);
    
    if (response.dfmIssues) {
      response.dfmIssues.forEach(issue => {
        console.warn(`DFM issue: ${issue.description}`);
      });
    }
  }
}
```

## Testing

To test the API integration:

1. Start the Python backend
2. Run the test script:
   ```bash
   ./test-api-python.sh
   ```
3. Run the Next.js frontend:
   ```bash
   npm run dev
   ``` 