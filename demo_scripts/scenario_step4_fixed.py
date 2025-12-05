import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 4: Check Alerts (Improved)
print("👤 User Action: Checking Alerts Dashboard for the blocked incident (Deep Search)...")

response = requests.get(f"{BASE_URL}/api/alerts/")

if response.status_code == 200:
    alerts = response.json()
    found_blocked = False
    
    print(f"Scanning {len(alerts)} alerts...")
    
    for alert in alerts:
        # Check if this alert is related to a blocking action
        if alert.get("blocked") is True:
            print("\n🔎 Found Blocked Alert:")
            print(json.dumps(alert, indent=2))
            found_blocked = True
            break # Found the evidence we needed
            
    if found_blocked:
         print("\n✅ Audit Trail Verified: A blocking alert exists in the logs.")
    else:
         print("\n❌ Audit Trail Failure: No blocking alert found.")

else:
    print(f"Error: {response.status_code} - {response.text}")

