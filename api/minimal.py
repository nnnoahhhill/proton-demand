from http.server import BaseHTTPRequestHandler
import json

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
        # Add CORS headers to all responses
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Simple mock response
        response = {
            "success": True,
            "quoteId": "test-123456",
            "price": 199.99,
            "currency": "USD",
            "leadTimeInDays": 7,
            "manufacturingDetails": {
                "process": "CNC",
                "material": "aluminum_6061",
                "finish": "standard",
                "boundingBox": {
                    "x": 100,
                    "y": 80,
                    "z": 40
                },
                "volume": 250000,
                "surfaceArea": 30000
            },
            "message": "This is a minimal test response"
        }
        
        self.wfile.write(json.dumps(response).encode()) 