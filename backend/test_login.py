"""Test login API endpoint"""
import requests
import json

url = "http://127.0.0.1:8000/api/auth/login"
data = {
    "username": "admin",
    "password": "admin123"
}

print(f"Testing login endpoint: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
    except:
        print(f"Response Text: {response.text[:500]}")
        
except requests.exceptions.ConnectionError:
    print("\n[ERROR] Cannot connect to server. Is the server running?")
except Exception as e:
    print(f"\n[ERROR] {e}")

