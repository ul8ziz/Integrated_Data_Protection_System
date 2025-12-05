import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("\n--- Testing Health Endpoint ---")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def test_analysis():
    print("\n--- Testing Text Analysis (Regex Fallback) ---")
    payload = {
        "text": "Hello, my email is test@example.com and phone is 0501234567",
        "apply_policies": False
    }
    try:
        response = requests.post(f"{BASE_URL}/api/analyze/", json=payload)
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Check if entities were detected
        entities = result.get("detected_entities", [])
        if len(entities) > 0:
             print(f"✅ Analysis passed. Detected {len(entities)} entities.")
        else:
             print("⚠️ Analysis returned no entities.")
             
    except Exception as e:
        print(f"❌ Analysis error: {e}")

def test_policies():
    print("\n--- Testing Policies Endpoint ---")
    try:
        response = requests.get(f"{BASE_URL}/api/policies/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            policies = response.json()
            print(f"✅ Policies check passed. Found {len(policies)} policies.")
        else:
            print("❌ Policies check failed")
    except Exception as e:
         print(f"❌ Policies error: {e}")

def test_frontend():
    print("\n--- Testing Frontend ---")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200 and "html" in response.headers.get("Content-Type", ""):
            print("✅ Frontend loaded successfully")
        else:
            print(f"❌ Frontend failed to load. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

if __name__ == "__main__":
    print("Starting System Checks...")
    time.sleep(1)
    test_health()
    test_policies()
    test_analysis()
    test_frontend()
