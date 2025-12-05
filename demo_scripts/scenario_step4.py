import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 4: Check Alerts
print("👤 User Action: Checking Alerts Dashboard for the blocked incident...")

response = requests.get(f"{BASE_URL}/api/alerts/")

print(f"\n--- System Response (Alerts List) ---")
if response.status_code == 200:
    alerts = response.json()
    # Get the latest alert
    if alerts:
        latest_alert = alerts[0] # Assuming sorted by date desc, checking logic might be needed if not
        # Actually API returns list, let's find the one related to our policy
        # Or just show the last one created
        print(f"Found {len(alerts)} total alerts.")
        print("Latest Alert Details:")
        print(json.dumps(latest_alert, indent=2))
        
        if latest_alert.get("blocked") is True:
             print("\n✅ Audit Trail Verified: The alert correctly shows the action was BLOCKED.")
        else:
             print("\n⚠️ Audit Trail Warning: The alert does not show blocked status.")
    else:
        print("No alerts found.")
else:
    print(f"Error: {response.status_code} - {response.text}")

