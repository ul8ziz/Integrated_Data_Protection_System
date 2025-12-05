import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 2: Create/Update Policy
print("👤 User Action: Creating a strict BLOCK policy for Phone Numbers...")

# First, create a new strict policy
policy_data = {
    "name": "Strict Phone Blocking",
    "description": "Block any communication containing phone numbers immediately",
    "entity_types": ["PHONE_NUMBER"],
    "action": "block",
    "severity": "high",
    "enabled": True
}

response = requests.post(
    f"{BASE_URL}/api/policies/",
    json=policy_data
)

print(f"\n--- System Response (Policy Creation) ---")
if response.status_code == 200:
    print("✅ Policy 'Strict Phone Blocking' created successfully!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Error creating policy: {response.text}")

