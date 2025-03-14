#!/bin/bash

# Test script for the Python API /api/getQuote endpoint

# URL where the Python API is running
API_URL="http://localhost:8000/api/getQuote"

# Test model paths
CNC_MODEL="./test-models/CNC_Nozzle.stl"
DP_MODEL="./test-models/3DP_CupHolder.stl" 
SM_MODEL="./test-models/SM_DrainGrate.stl"

# Test CNC Machining Quote
echo "Testing CNC Machining Quote..."
curl -X POST \
  -F "process=CNC" \
  -F "material=aluminum_6061" \
  -F "finish=standard" \
  -F "model_file=@$CNC_MODEL" \
  $API_URL

echo -e "\n\n"

# Test 3D Printing (SLA) Quote
echo "Testing 3D Printing (SLA) Quote..."
curl -X POST \
  -F "process=3DP_SLA" \
  -F "material=resin_standard" \
  -F "finish=standard" \
  -F "model_file=@$DP_MODEL" \
  $API_URL

echo -e "\n\n"

# Test 3D Printing (FDM) Quote
echo "Testing 3D Printing (FDM) Quote..."
curl -X POST \
  -F "process=3DP_FDM" \
  -F "material=pla" \
  -F "finish=standard" \
  -F "model_file=@$DP_MODEL" \
  $API_URL

echo -e "\n\n"

echo "All tests completed." 