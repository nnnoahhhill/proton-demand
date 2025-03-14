# `/getQuote` API Endpoint

This document describes the simplified `/getQuote` API endpoint for obtaining manufacturing quotes.

## Endpoint Details

- **URL**: `/api/getQuote`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| process | String | Yes | Manufacturing process. Valid values: `CNC`, `3DP_SLA`, `3DP_SLS`, `3DP_FDM`, `SHEET_METAL` |
| material | String | Yes | Material to use (specific to the selected process) |
| finish | String | Yes | Surface finish quality (specific to the selected process and material) |
| modelFile | File | Yes | 3D model file (.stl, .step, or .stp) |
| drawingFile | File | No | Optional engineering drawing (.pdf) |

## Valid Materials by Process

### CNC Machining (`CNC`)
- `ALUMINUM_6061`
- `MILD_STEEL`
- `STAINLESS_STEEL_304`
- `STAINLESS_STEEL_316`
- `TITANIUM`
- `COPPER`
- `BRASS`
- `HDPE`
- `POM_ACETAL`
- `ABS`
- `ACRYLIC`
- `NYLON`
- `PEEK`
- `PC`

### 3D Printing SLA (`3DP_SLA`)
- `STANDARD_RESIN`

### 3D Printing SLS (`3DP_SLS`)
- `NYLON_12_WHITE`
- `NYLON_12_BLACK`

### 3D Printing FDM (`3DP_FDM`)
- `PLA`
- `ABS`
- `NYLON_12`
- `ASA`
- `PETG`
- `TPU`

### Sheet Metal Fabrication (`SHEET_METAL`)
- `ALUMINUM_6061`
- `MILD_STEEL`
- `STAINLESS_STEEL_304`
- `STAINLESS_STEEL_316`
- `TITANIUM`
- `COPPER`
- `BRASS`

## Valid Finishes by Process

### CNC Machining (`CNC`)
- `STANDARD`
- `FINE`
- `MIRROR`

### 3D Printing SLA (`3DP_SLA`)
- `STANDARD`
- `FINE`

### 3D Printing SLS (`3DP_SLS`)
- `STANDARD`

### 3D Printing FDM (`3DP_FDM`)
- `STANDARD`
- `FINE`

### Sheet Metal Fabrication (`SHEET_METAL`)
- `STANDARD`
- `PAINTED`
- `ANODIZED`
- `POWDER_COATED`

## Successful Response

When the part can be manufactured, the endpoint returns a 200 OK response with a JSON object containing:

```json
{
  "success": true,
  "quoteId": "uuid-string",
  "price": 123.45,
  "currency": "USD",
  "leadTimeInDays": 5,
  "manufacturingDetails": {
    "process": "CNC",
    "material": "ALUMINUM_6061",
    "finish": "STANDARD",
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

## Error Response

When there are issues with the request or the part cannot be manufactured, the endpoint returns a 4xx error with a JSON object containing:

```json
{
  "success": false,
  "error": "Error message",
  "dfmIssues": [
    {
      "type": "thin_wall",
      "severity": "critical",
      "description": "Wall thickness of 0.3mm is below minimum threshold of 0.8mm for CNC machining",
      "location": {
        "x": 10,
        "y": 20,
        "z": 30
      }
    }
  ]
}
```

## Example Usage (curl)

```bash
curl -X POST \
  -F "process=CNC" \
  -F "material=ALUMINUM_6061" \
  -F "finish=STANDARD" \
  -F "modelFile=@./path/to/model.stl" \
  http://your-domain.com/api/getQuote
``` 