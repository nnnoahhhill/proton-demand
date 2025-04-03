from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import subprocess
import tempfile
import uuid
import traceback
from urllib.parse import parse_qs

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define the valid materials and processes exactly as in manufacturing_dfm_api.py
VALID_PROCESSES = ['CNC', '3DP_SLA', '3DP_SLS', '3DP_FDM', 'SHEET_METAL']

# Validate materials based on process - EXACTLY as in the manufacturing_dfm_api.py
VALID_MATERIALS = {
    'CNC': [
        'ALUMINUM_6061', 'MILD_STEEL', 'STAINLESS_STEEL_304', 'STAINLESS_STEEL_316', 
        'TITANIUM', 'COPPER', 'BRASS', 'HDPE', 'POM_ACETAL', 'ABS', 
        'ACRYLIC', 'NYLON', 'PEEK', 'PC'
    ],
    '3DP_SLA': ['STANDARD_RESIN'],
    '3DP_SLS': ['NYLON_12_WHITE', 'NYLON_12_BLACK'],
    '3DP_FDM': ['PLA', 'ABS', 'NYLON_12', 'ASA', 'PETG', 'TPU'],
    'SHEET_METAL': [
        'ALUMINUM_6061', 'MILD_STEEL', 'STAINLESS_STEEL_304', 'STAINLESS_STEEL_316', 
        'TITANIUM', 'COPPER', 'BRASS'
    ]
}

# Validate finishes based on process - EXACTLY as in the manufacturing_dfm_api.py
VALID_FINISHES = {
    'CNC': ['STANDARD', 'FINE', 'MIRROR'],
    '3DP_SLA': ['STANDARD', 'FINE'],
    '3DP_SLS': ['STANDARD'],
    '3DP_FDM': ['STANDARD', 'FINE'],
    'SHEET_METAL': ['STANDARD', 'PAINTED', 'ANODIZED', 'POWDER_COATED']
}

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.end_headers()
        
    def do_POST(self):
        try:
            # Get content length to read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Debug info before we send headers
            content_type = self.headers.get('Content-Type', '')
            print(f"Content-Length: {content_length}, Content-Type: {content_type}")
            
            # Now add CORS headers to all responses AFTER getting the headers
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Check if this is a multipart/form-data request
            if not content_type.startswith('multipart/form-data'):
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'Request must be multipart/form-data, received: {content_type}'
                }).encode())
                return
                
            # Extract boundary
            try:
                boundary = content_type.split('=')[1].strip().encode()
                print(f"Boundary found: {boundary.decode()}")
            except (IndexError, AttributeError) as e:
                print(f"Boundary extraction error: {str(e)}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'Invalid content type boundary: {content_type}'
                }).encode())
                return
            
            # Read request body
            try:
                body = self.rfile.read(content_length)
                print(f"Read {len(body)} bytes from request body")
            except Exception as e:
                print(f"Error reading request body: {str(e)}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'Error reading request body: {str(e)}'
                }).encode())
                return
                
            # Process multipart form data
            temp_dir = tempfile.mkdtemp()
            quote_id = str(uuid.uuid4())
            print(f"Processing request {quote_id} in temporary directory {temp_dir}")
            
            # Parse multipart form data
            try:
                form_data = self.parse_multipart_form(body, boundary, temp_dir)
                print(f"Parsed form data keys: {list(form_data.keys())}")
            except Exception as e:
                traceback.print_exc()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'Error parsing multipart form: {str(e)}'
                }).encode())
                return
                
            # Check for file - could be named 'file' or 'model_file' based on frontend
            file_path = None
            if 'model_file' in form_data:
                print("Found model_file in form data")
                model_file_data = form_data['model_file']
                if isinstance(model_file_data, list):
                    file_path = model_file_data[0] if model_file_data else None
                    print(f"model_file is a list, using first item: {file_path}")
                else:
                    file_path = model_file_data
                    print(f"model_file is direct value: {file_path}")
            elif 'file' in form_data:
                print("Found file in form data")
                file_data = form_data['file']
                if isinstance(file_data, list):
                    file_path = file_data[0] if file_data else None
                    print(f"file is a list, using first item: {file_path}")
                else:
                    file_path = file_data
                    print(f"file is direct value: {file_path}")
                
            if not file_path:
                print(f"No file path found in form data keys: {list(form_data.keys())}")
                
                # If we can't find a file, check if any files were saved in the temp_dir
                temp_files = os.listdir(temp_dir)
                if temp_files:
                    file_path = os.path.join(temp_dir, temp_files[0])
                    print(f"Found file in temp directory: {file_path}")
                else:
                    self.wfile.write(json.dumps({
                        "success": False,
                        "error": 'No model file provided. Please upload a .stl or .step file.'
                    }).encode())
                    return
                
            # Verify file exists
            if not os.path.exists(file_path):
                print(f"File path does not exist: {file_path}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'File was uploaded but not found at path: {file_path}'
                }).encode())
                return
                
            print(f"File exists at {file_path}, size: {os.path.getsize(file_path)} bytes")
                
            # Get form parameters with better error handling
            process_type = None
            if 'process' in form_data:
                process_data = form_data['process']
                if isinstance(process_data, list):
                    process_type = process_data[0] if process_data else ''
                else:
                    process_type = process_data
            
            if not process_type:
                process_type = 'CNC'  # Default to CNC if not provided
                
            material = None
            if 'material' in form_data:
                material_data = form_data['material']
                if isinstance(material_data, list):
                    material = material_data[0] if material_data else ''
                else:
                    material = material_data
                
            if not material:
                # Default based on process type
                if process_type == '3DP_SLA':
                    material = 'STANDARD_RESIN'
                elif process_type == 'CNC':
                    material = 'ALUMINUM_6061'
                elif process_type == '3DP_FDM':
                    material = 'PLA'
                elif process_type == '3DP_SLS':
                    material = 'NYLON_12_WHITE'
                elif process_type == 'SHEET_METAL':
                    material = 'ALUMINUM_6061'
                    
            # Convert material to uppercase to match backend expectations
            material = material.upper()
                
            finish = None
            if 'finish' in form_data:
                finish_data = form_data['finish']
                if isinstance(finish_data, list):
                    finish = finish_data[0] if finish_data else ''
                else:
                    finish = finish_data
                
            if not finish:
                finish = 'STANDARD'  # Default to STANDARD if not provided
                
            # Convert finish to uppercase to match backend expectations
            finish = finish.upper()
            
            # Get original filename if provided
            original_filename = None
            if 'original_filename' in form_data:
                original_filename = form_data['original_filename']
                print(f"Using original filename: {original_filename}")
            
            print(f"Analyzing file: {file_path}")
            print(f"Parameters: process={process_type}, material={material}, finish={finish}")
            
            # Validate process type
            if process_type not in VALID_PROCESSES:
                print(f"Invalid process: {process_type}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f"Invalid process type: {process_type}. Must be one of: {', '.join(VALID_PROCESSES)}"
                }).encode())
                return
                
            # Validate material for the selected process
            if material not in VALID_MATERIALS.get(process_type, []):
                print(f"Invalid material for process {process_type}: {material}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f"Invalid material for {process_type}. Must be one of: {', '.join(VALID_MATERIALS.get(process_type, []))}"
                }).encode())
                return
                
            # Validate finish for the selected process
            if finish not in VALID_FINISHES.get(process_type, []):
                print(f"Invalid finish for process {process_type}: {finish}")
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f"Invalid finish for {process_type}. Must be one of: {', '.join(VALID_FINISHES.get(process_type, []))}"
                }).encode())
                return
                
            # Run DFM analysis using the module
            result = self.run_dfm_analysis(file_path, process_type, material, finish)
            
            # Add original filename to response if available
            if original_filename and 'success' in result and result['success']:
                if 'manufacturingDetails' not in result:
                    result['manufacturingDetails'] = {}
                result['manufacturingDetails']['filename'] = original_filename
            
            # Clean up
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Removed temporary file: {file_path}")
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    print(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
                
            # Send the result
            print(f"Sending response: {json.dumps(result)[:100]}...")
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            traceback.print_exc()
            try:
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": f'Unhandled server error: {str(e)}'
                }).encode())
            except:
                # Already sent headers
                pass
    
    def parse_multipart_form(self, body, boundary, temp_dir):
        print("Starting multipart form parsing")
        form_data = {}
        
        try:
            # Use a more robust approach to handle spaces in filenames
            boundary_str = b'--' + boundary
            parts = body.split(boundary_str)
            print(f"Split request into {len(parts)} parts")
            
            # Print raw data for debugging (just the first 100 chars to keep logs clean)
            print(f"Raw data excerpt: {body[:100]}")
            
            for i, part in enumerate(parts):
                # Skip empty parts
                if len(part) < 4:
                    continue
                    
                # Skip final boundary part (usually '--\r\n')
                if i == len(parts) - 1 and b'--' in part[:4]:
                    continue
                    
                # Skip first part if it's empty (which it often is)
                if i == 0 and not part.strip():
                    continue
                
                print(f"Processing part {i}, length: {len(part)}")
                
                # Find the header and content sections
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    print(f"No header end found in part {i}")
                    continue
                
                headers_raw = part[:header_end].strip()
                content = part[header_end + 4:].strip(b'\r\n--')
                
                # Parse headers
                headers = {}
                for header_line in headers_raw.split(b'\r\n'):
                    try:
                        # Skip empty lines
                        if not header_line:
                            continue
                            
                        # Decode header line
                        header_line_str = header_line.decode('utf-8', errors='ignore')
                        
                        # Split at the first colon
                        if ':' in header_line_str:
                            key, value = header_line_str.split(':', 1)
                            headers[key.strip().lower()] = value.strip()
                    except Exception as e:
                        print(f"Error parsing header line: {e}")
                
                # Get Content-Disposition parameters
                field_name = None
                filename = None
                
                if 'content-disposition' in headers:
                    content_disp = headers['content-disposition']
                    print(f"Content-Disposition: {content_disp}")
                    
                    # Parse parameters
                    for param in content_disp.split(';'):
                        param = param.strip()
                        if '=' in param:
                            key, value = [p.strip() for p in param.split('=', 1)]
                            
                            # Remove quotes around values
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                                
                            if key == 'name':
                                field_name = value
                            elif key == 'filename':
                                filename = value
                
                if not field_name:
                    print(f"No field name found in part {i}")
                    continue
                    
                print(f"Field name: {field_name}, Filename: {filename}")
                
                # Handle file upload
                if filename:
                    print(f"Found file upload: field={field_name}, filename={filename}")
                    
                    # Create a safe filename
                    safe_filename = os.path.basename(filename)
                    file_path = os.path.join(temp_dir, safe_filename)
                    
                    # Write file content
                    with open(file_path, 'wb') as f:
                        f.write(content)
                        
                    print(f"Saved file to {file_path}, size={len(content)} bytes")
                    form_data[field_name] = file_path
                else:
                    # Handle regular form fields
                    field_value = content.decode('utf-8', errors='ignore')
                    print(f"Form field: {field_name}={field_value}")
                    form_data[field_name] = field_value
            
            print(f"Parsed form data: {form_data}")
            return form_data
            
        except Exception as e:
            print(f"Error in parse_multipart_form: {str(e)}")
            traceback.print_exc()
            raise
    
    def run_dfm_analysis(self, file_path, process_type, material, finish):
        """Run the DFM analysis on the uploaded file"""
        try:
            # Verify the file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
                
            # Return mock data for quicker testing on Vercel
            # Comment this out when you want to use the real DFM analysis
            print("Providing mock DFM response for faster testing")
            return {
                "success": True,
                "quoteId": str(uuid.uuid4()),
                "price": 249.99,
                "currency": "USD",
                "leadTimeInDays": 10,
                "manufacturingDetails": {
                    "process": process_type,
                    "material": material,
                    "finish": finish,
                    "boundingBox": {
                        "x": 100,
                        "y": 80,
                        "z": 40
                    },
                    "volume": 320000,
                    "surfaceArea": 36800,
                    "printabilityScore": 85,
                    "estimatedPrintTime": "8h 45m"
                },
                "dfmIssues": [
                    {
                        "type": "wall_thickness",
                        "severity": "warning",
                        "description": "Wall thickness of 0.8mm is below recommended minimum of 1.0mm"
                    }
                ]
            }
            
            # Uncomment the following for real DFM analysis
            """
            # Convert process to Python enum format
            python_process = ''
            if process_type == 'CNC':
                python_process = 'cnc_machining'
            elif process_type.startswith('3DP_'):
                python_process = '3d_printing'
            elif process_type == 'SHEET_METAL':
                python_process = 'sheet_metal'

            # For 3D printing, specify the technology
            printing_tech = ''
            if process_type == '3DP_SLA':
                printing_tech = '--printing_technology sla'
            elif process_type == '3DP_SLS':
                printing_tech = '--printing_technology sls'
            elif process_type == '3DP_FDM':
                printing_tech = '--printing_technology fdm'

            # Run the Python script
            cmd = f"python dfm/manufacturing_dfm_api.py analyze --file '{file_path}' --method {python_process} --material {material} --finish {finish.lower()} {printing_tech} --detailed true"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"DFM analysis failed: {result.stderr}"
                }
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse DFM analysis result",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            """
                
        except Exception as e:
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Error running DFM analysis: {str(e)}"
            }
    
    def send_error_response(self, message):
        """No longer used - keeping for reference"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": False,
            "error": message
        }).encode()) 