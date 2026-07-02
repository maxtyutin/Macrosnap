import http.server
import socketserver
import urllib.request
import json
import os
import random

PORT = 8888

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/gemini':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Google Gemini 3.5 Flash API endpoint
            gemini_key = "AIzaSyAkVJfTnwZ4GnEEmD8SsCY86gjL_xwPw70"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={gemini_key}"
            
            req = urllib.request.Request(
                url,
                data=post_data,
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = response.read()
                    
                    # Log response to workspace file for debugging
                    with open("gemini_response.log", "w", encoding="utf-8") as f:
                        f.write(res_data.decode("utf-8", errors="ignore"))
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(res_data)
            except Exception as e:
                # Log error
                with open("gemini_response.log", "w", encoding="utf-8") as f:
                    f.write(f"ERROR: {str(e)}")
                    
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/api/send-code':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                email = data.get('email', '')
                code = str(random.randint(1000, 9999))
                
                print(f"\n[MAIL SERVER] Sending confirmation code {code} to {email}\n")
                
                # Append to browser_console.log so the frontend logs capture it for convenience
                with open("browser_console.log", "a", encoding="utf-8") as f:
                    f.write(f"console.log: [MAIL SERVER] Sent verification code {code} to {email}\n")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True, 'code': code, 'email': email}
                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/api/log':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                log_data = json.loads(post_data.decode("utf-8"))
                msg = log_data.get('message', '')
                with open("browser_console.log", "a", encoding="utf-8") as f:
                    f.write(f"{msg}\n")
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
            except Exception as e:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        return super().do_GET()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Local Proxy Server running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
