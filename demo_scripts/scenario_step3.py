import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 3: Re-analyze text
print("👤 User Action: Re-sending the same suspicious text after policy update...")
text = "This is regarding the CONFIDENTIAL PROJECT Alpha. Call me at 0501234567"
response = requests.post(
    f"{BASE_URL}/api/analyze/",
    json={"text": text, "apply_policies": True}
)

print(f"\n--- System Response (Post-Policy Analysis) ---")
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
    
    if data.get("blocked") is True:
        print("\n✅ SUCCESS: The data transfer was BLOCKED as expected!")
    else:
        print("\n❌ FAILURE: The data was NOT blocked.")
else:
    print(f"Error: {response.status_code} - {response.text}")

