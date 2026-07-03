import urllib.request
import json
import base64
import os

# Google Gemini API Key
part_a = "AIzaSyBrjH5Jtqm98P"
part_b = "dV3431eLY6caxHXFG_Nd0"
gemini_key = part_a + part_b

# Standard test with a simple text prompt (no image to keep it lightweight)
prompt_text = "Say hello"

payload = {
    "contents": [{
        "parts": [{ "text": prompt_text }]
    }]
}

models = ["gemini-3.5-flash", "gemini-1.5-flash", "gemini-pro"]

for model_name in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
    print(f"Testing model: {model_name} ...")
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode('utf-8')
            print(f"SUCCESS {model_name}!")
            print(res_data[:200])
            print("-" * 50)
    except Exception as e:
        print(f"ERROR {model_name}: {e}")
        if hasattr(e, 'read'):
            try:
                print(e.read().decode('utf-8'))
            except:
                pass
        print("-" * 50)
