import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_email_interception():
    print("\n📧 --- Email Interception Scenario ---")
    
    # 1. Prepare a suspicious email
    email_payload = {
        "from": "employee@company.com",
        "to": ["external_competitor@gmail.com"],
        "subject": "Project X Files",
        "body": "Please find attached the secret blueprint. Also, use this credit card for the fees: 4532-1234-5678-9012. Don't tell anyone."
    }
    
    print("\n👤 User: Sending email to external recipient with sensitive data...")
    print(f"   From: {email_payload['from']}")
    print(f"   To: {email_payload['to']}")
    print(f"   Content: \"{email_payload['body']}\"")
    
    # 2. Send to DLP System for inspection
    print("\n🔄 System: Intercepting and analyzing email...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/monitoring/email",
            json=email_payload
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n📊 System Verdict:")
            print(json.dumps(result, indent=2))
            
            # 3. Verify Result
            if result.get("blocked") is True:
                print("\n🛡️ SUCCESS: Email was INTERCEPTED and BLOCKED.")
                print(f"   Reason: {result.get('message')}")
                print("   Action: The email will NOT be delivered.")
            else:
                if result.get("sensitive_data_detected"):
                     print("\n⚠️ WARNING: Sensitive data detected but NOT blocked (Alert only).")
                     print("   The email WOULD be delivered but flagged.")
                else:
                     print("\n❌ FAILURE: Sensitive data was NOT detected.")
        else:
            print(f"\n❌ Error: API request failed ({response.status_code})")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_email_interception()

