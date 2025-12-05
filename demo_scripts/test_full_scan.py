import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(message, status="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "PASS":
        print(f"[{timestamp}] {GREEN}PASS{RESET}: {message}")
    elif status == "FAIL":
        print(f"[{timestamp}] {RED}FAIL{RESET}: {message}")
    elif status == "WARN":
        print(f"[{timestamp}] {YELLOW}WARN{RESET}: {message}")
    else:
        print(f"[{timestamp}] INFO: {message}")

def test_clean_text():
    log("Testing clean text analysis...", "INFO")
    payload = {
        "text": "Hello, this is a normal meeting regarding the project updates.",
        "apply_policies": True
    }
    try:
        response = requests.post(f"{BASE_URL}/api/analyze/", json=payload)
        if response.status_code == 200:
            result = response.json()
            if not result.get("sensitive_data_detected", False):
                log("Clean text passed (no false positives).", "PASS")
            else:
                log(f"Clean text failed (detected: {result.get('detected_entities')})", "FAIL")
        else:
            log(f"Request failed with status {response.status_code}", "FAIL")
    except Exception as e:
        log(f"Error: {e}", "FAIL")

def test_sensitive_data_detection():
    log("Testing sensitive data detection (Email, Phone, Credit Card)...", "INFO")
    # Note: Using a fake credit card pattern that might match the regex
    payload = {
        "text": "Please contact ali@example.com or call 0551234567. CC: 4532-1234-5678-9012",
        "apply_policies": True
    }
    try:
        response = requests.post(f"{BASE_URL}/api/analyze/", json=payload)
        if response.status_code == 200:
            result = response.json()
            entities = result.get("detected_entities", [])
            
            # Check for specific entities
            has_email = any(e['entity_type'] == 'EMAIL_ADDRESS' for e in entities)
            has_phone = any(e['entity_type'] == 'PHONE_NUMBER' for e in entities)
            has_cc = any(e['entity_type'] == 'CREDIT_CARD' for e in entities)
            
            if has_email and has_phone:
                 log(f"Detected Email and Phone correctly. (Total: {len(entities)})", "PASS")
            elif has_email or has_phone:
                 log(f"Partially detected entities. Found: {[e['entity_type'] for e in entities]}", "WARN")
            else:
                 log("Failed to detect sensitive data.", "FAIL")
                 
            if result.get("sensitive_data_detected") is True:
                log("Flag 'sensitive_data_detected' is set to True.", "PASS")
        else:
            log(f"Request failed with status {response.status_code}", "FAIL")
    except Exception as e:
        log(f"Error: {e}", "FAIL")

def test_email_monitoring_simulation():
    log("Testing Email Monitoring endpoint...", "INFO")
    payload = {
        "from": "employee@company.com",
        "to": ["outsider@gmail.com"],
        "subject": "Confidential Project",
        "body": "Here is the secret key: 1234-5678-9012-3456 and my phone 0509998877"
    }
    try:
        # Note: The endpoint might be /api/monitoring/email based on earlier review
        # Let's verify the endpoint path by trying likely candidates or checking code
        # Checking code: api/routes/monitoring.py -> router mounted at /api/monitoring
        # Function analyze_email -> post("/email")
        response = requests.post(f"{BASE_URL}/api/monitoring/email", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # Expected: Blocked or Alerted
            if result.get("status") == "blocked" or result.get("action") == "blocked":
                 log("Email with sensitive data was BLOCKED/FLAGGED correctly.", "PASS")
            elif result.get("alerts_generated", False):
                 log("Email generated alerts successfully.", "PASS")
            else:
                 log(f"Email processed but outcome unclear: {result}", "WARN")
        else:
             # Sometimes endpoints might be named differently, let's print error
             log(f"Email monitoring request failed: {response.status_code} - {response.text}", "FAIL")
    except Exception as e:
        log(f"Error: {e}", "FAIL")

def test_alerts_generation():
    log("Checking if alerts were logged in the system...", "INFO")
    try:
        response = requests.get(f"{BASE_URL}/api/alerts/")
        if response.status_code == 200:
            alerts = response.json()
            if len(alerts) > 0:
                log(f"Found {len(alerts)} alerts in the system.", "PASS")
                log(f"Latest alert: {alerts[0].get('description', 'No description')}", "INFO")
            else:
                log("No alerts found (Verify if previous tests should have triggered them).", "WARN")
        else:
            log(f"Failed to fetch alerts: {response.status_code}", "FAIL")
    except Exception as e:
        log(f"Error: {e}", "FAIL")

def run_full_scan():
    print("\n" + "="*40)
    print("      STARTING COMPREHENSIVE SYSTEM TEST      ")
    print("="*40 + "\n")
    
    # Ensure server is up
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        log("Server is NOT responding. Make sure it is running.", "FAIL")
        return

    test_clean_text()
    time.sleep(1)
    test_sensitive_data_detection()
    time.sleep(1)
    test_email_monitoring_simulation()
    time.sleep(1)
    test_alerts_generation()
    
    print("\n" + "="*40)
    print("      TEST COMPLETE      ")
    print("="*40 + "\n")

if __name__ == "__main__":
    run_full_scan()

