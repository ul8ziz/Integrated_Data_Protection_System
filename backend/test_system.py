"""
Test script for the system
"""
import sys
import requests
import time

def test_system():
    """Test the system endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing Athier Data Protection System...")
    print("=" * 50)
    
    # Wait for server to start
    print("\n1. Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print("   [OK] Server is running!")
                break
        except:
            time.sleep(1)
            print(f"   Waiting... ({i+1}/10)")
    else:
        print("   [ERROR] Server is not responding")
        return False
    
    # Test health endpoint
    print("\n2. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   [OK] Health check: {response.json()}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        return False
    
    # Test analysis endpoint
    print("\n3. Testing text analysis...")
    try:
        test_text = "My name is John Doe and my phone is 123-456-7890. Email: test@example.com"
        response = requests.post(
            f"{base_url}/api/analyze/",
            json={
                "text": test_text,
                "apply_policies": False
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Analysis successful!")
            print(f"   - Sensitive data detected: {result['sensitive_data_detected']}")
            print(f"   - Entities found: {len(result['detected_entities'])}")
            for entity in result['detected_entities']:
                print(f"     - {entity['entity_type']}: {entity['value']} (confidence: {entity['score']:.2f})")
        else:
            print(f"   [ERROR] Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test policies endpoint
    print("\n4. Testing policies endpoint...")
    try:
        response = requests.get(f"{base_url}/api/policies/")
        if response.status_code == 200:
            policies = response.json()
            print(f"   [OK] Policies endpoint working! ({len(policies)} policies)")
        else:
            print(f"   [ERROR] Error: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test alerts endpoint
    print("\n5. Testing alerts endpoint...")
    try:
        response = requests.get(f"{base_url}/api/alerts/")
        if response.status_code == 200:
            alerts = response.json()
            print(f"   [OK] Alerts endpoint working! ({len(alerts)} alerts)")
        else:
            print(f"   [ERROR] Error: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test monitoring endpoint
    print("\n6. Testing monitoring endpoint...")
    try:
        response = requests.get(f"{base_url}/api/monitoring/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   [OK] Monitoring endpoint working!")
            print(f"   - System status: {status['status']}")
            print(f"   - Presidio: {status['presidio']['status']}")
            print(f"   - MyDLP: {status['mydlp']['status']} (enabled: {status['mydlp']['enabled']})")
        else:
            print(f"   [ERROR] Error: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    print("\n" + "=" * 50)
    print("Testing completed!")
    return True

if __name__ == "__main__":
    try:
        test_system()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()

