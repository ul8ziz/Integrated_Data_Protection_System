import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_response(step, response):
    print(f"\n--- {step} ---")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code} - {response.text}")

# Step 1: Analyze text
print("👤 User Action: Analyzing suspicious text...")
text = "This is regarding the CONFIDENTIAL PROJECT Alpha. Call me at 0501234567"
response = requests.post(
    f"{BASE_URL}/api/analyze/",
    json={"text": text, "apply_policies": True}
)
print_response("System Response (Initial Analysis)", response)

