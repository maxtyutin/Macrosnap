import urllib.request
import json

part_a = "AIzaSyBrjH5Jtqm98P"
part_b = "dV3431eLY6caxHXFG_Nd0"
gemini_key = part_a + part_b

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"

req = urllib.request.Request(url, headers={'Content-Type': 'application/json'}, method='GET')
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        res = json.loads(response.read().decode('utf-8'))
        print("Models list:")
        for m in res.get('models', []):
            print(f"Name: {m.get('name')} | DisplayName: {m.get('displayName')} | Methods: {m.get('supportedGenerationMethods')}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        try:
            print(e.read().decode('utf-8'))
        except:
            pass
