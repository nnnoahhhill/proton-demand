from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.end_headers()
    
    def do_GET(self):
        self._handle_request()
        
    def do_POST(self):
        self._handle_request()
        
    def _handle_request(self):
        # Always return a successful response for this test endpoint
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Return a simple test response
        response = {
            "success": True,
            "message": "API test endpoint is working correctly",
            "server_info": {
                "endpoint": "/api/test",
                "handler": "BaseHTTPRequestHandler"
            }
        }
        
        self.wfile.write(json.dumps(response).encode()) 