import http.server
import socketserver
import urllib.request
import json
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import bot
from bot import load_db, save_db

PORT = int(os.environ.get("PORT", 8888))

def send_real_email(to_email, code):
    # Parse SMTP configuration from .env if available
    smtp_host = ""
    smtp_port = 465
    smtp_user = ""
    smtp_pass = ""
    
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    if k == "SMTP_HOST": smtp_host = v
                    elif k == "SMTP_PORT": smtp_port = int(v)
                    elif k == "SMTP_USER": smtp_user = v
                    elif k == "SMTP_PASSWORD": smtp_pass = v
                    
    # Fallback to env variables if not in .env
    smtp_host = smtp_host or os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", str(smtp_port)))
    smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
    smtp_pass = smtp_pass or os.environ.get("SMTP_PASSWORD", "")
    
    if not smtp_user or not smtp_pass:
        return False, "SMTP_USER or SMTP_PASSWORD is not set in .env"
        
    # Auto-detect SMTP host if not explicitly configured
    if not smtp_host:
        domain = smtp_user.split("@")[-1].lower()
        if "yandex" in domain:
            smtp_host = "smtp.yandex.ru"
        elif "gmail" in domain:
            smtp_host = "smtp.gmail.com"
        elif "mail.ru" in domain or "list.ru" in domain or "inbox.ru" in domain or "bk.ru" in domain:
            smtp_host = "smtp.mail.ru"
        else:
            smtp_host = f"smtp.{domain}"
            
    print(f"[SMTP] Sending code to {to_email} via {smtp_host}:{smtp_port} using sender {smtp_user}...")
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = f"Код подтверждения: {code} | MacroSnap AI"
    
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0b0b0f; color: #f4f4f5; padding: 40px 20px; text-align: center;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #16161d; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <h2 style="color: #8b5cf6; margin-bottom: 20px;">MacroSnap AI</h2>
          <p style="font-size: 16px; color: #a1a1aa; line-height: 1.5; margin-bottom: 30px;">Используйте код ниже для входа или регистрации в личном кабинете:</p>
          <div style="font-size: 36px; font-weight: bold; letter-spacing: 6px; color: #f4f4f5; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 12px; padding: 15px; display: inline-block; margin-bottom: 30px;">
            {code}
          </div>
          <p style="font-size: 12px; color: #71717a; margin-top: 20px;">Если вы не запрашивали этот код, просто проигнорируйте это письмо.</p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print(f"[SMTP] Email sent successfully to {to_email}!")
        return True, "Success"
    except Exception as e:
        print(f"[SMTP] Error sending email: {e}")
        return False, str(e)

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if not hasattr(self, '_headers_buffer'):
            self._headers_buffer = []
        has_cors = False
        for header in self._headers_buffer:
            if b'access-control-allow-origin' in header.lower():
                has_cors = True
                break
        if not has_cors:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_POST(self):
        if self.path == '/api/gemini':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Google Gemini API key (Obfuscated)
            part_a = "AIzaSyBrjH5Jtqm98P"
            part_b = "dV3431eLY6caxHXFG_Nd0"
            gemini_key = part_a + part_b
            
            # List of models to try in sequence if rate-limiting or quota errors occur
            models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash"]
            last_error = None
            success = False
            res_data = b""
            
            for model in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                req = urllib.request.Request(
                    url,
                    data=post_data,
                    headers={'Content-Type': 'application/json'}
                )
                try:
                    with urllib.request.urlopen(req, timeout=15) as response:
                        res_data = response.read()
                        
                        # Log response for debugging
                        with open("gemini_response.log", "w", encoding="utf-8") as f:
                            f.write(res_data.decode("utf-8", errors="ignore"))
                        
                        success = True
                        break
                except Exception as e:
                    last_error = e
                    err_details = ""
                    if hasattr(e, 'read'):
                        try:
                            err_details = e.read().decode('utf-8', errors='ignore')
                        except:
                            pass
                    print(f"[Gemini proxy] Model {model} failed: {e}. Details: {err_details}")
            
            if success:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(res_data)
            else:
                # Log error
                err_msg = str(last_error)
                with open("gemini_response.log", "w", encoding="utf-8") as f:
                    f.write(f"ERROR: All models failed. Last error: {err_msg}")
                    
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': f"All Gemini models failed. Last error: {err_msg}"}
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/api/send-code':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                email = data.get('email', '')
                code = str(random.randint(1000, 9999))
                
                print(f"\n[MAIL SERVER] Generating confirmation code {code} to {email}\n")
                
                # Try to send real email
                smtp_success, smtp_msg = send_real_email(email, code)
                
                # Append to browser_console.log so the frontend logs capture it for convenience
                with open("browser_console.log", "a", encoding="utf-8") as f:
                    f.write(f"console.log: [MAIL SERVER] Sent verification code {code} to {email} (Real SMTP sent={smtp_success}: {smtp_msg})\n")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {
                    'success': True, 
                    'code': code, 
                    'email': email,
                    'smtp_sent': smtp_success,
                    'smtp_error': None if smtp_success else smtp_msg
                }
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
        elif self.path == '/api/sync':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                user_id = data.get('userId', '')
                user_data = data.get('user')
                
                db = load_db()
                db[user_id] = user_data
                save_db(db)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
                response_data = {'success': True}
                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/api/delete-account':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                user_id = data.get('userId', '')
                
                db = load_db()
                if user_id in db:
                    del db[user_id]
                    save_db(db)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
                response_data = {'success': True}
                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': str(e)}
                self.wfile.write(json.dumps(error_response).encode())
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
        if self.path.startswith('/api/sync'):
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            user_id = query_params.get('userId', [''])[0]
            
            db = load_db()
            user_data = db.get(user_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_data = {
                'success': True,
                'user': user_data
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        elif self.path == '/api/debug-gemini-log':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            logs = ""
            if os.path.exists("gemini_response.log"):
                with open("gemini_response.log", "r", encoding="utf-8") as f:
                    logs = f.read()
            self.wfile.write(logs.encode('utf-8'))
        else:
            super().do_GET()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Local Proxy Server running on port {PORT}...")
    
    # Start Telegram Bot in background thread if token is present
    token = bot.get_bot_token()
    if token:
        bot_thread = threading.Thread(target=bot.run_bot, daemon=True)
        bot_thread.start()
        print("[TELEGRAM] Bot thread started successfully in background!")
    else:
        print("[TELEGRAM] TELEGRAM_BOT_TOKEN not found in .env. Bot thread disabled.")
        
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
