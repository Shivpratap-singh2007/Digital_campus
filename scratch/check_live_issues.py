import urllib.request
import json

req = urllib.request.Request("https://digital-campus-sczg.onrender.com/api/issues")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("Issues count:", len(data.get("issues", [])))
    print("Issues:", data.get("issues", []))

