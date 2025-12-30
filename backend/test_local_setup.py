"""
Test script for local MyDLP setup and email monitoring
"""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_result(success, message):
    """Print test result"""
    symbol = "✓" if success else "✗"
    status = "OK" if success else "FAILED"
    print(f"{symbol} {message} - {status}")

def test_Secure_health():
    """Test Secure API health"""
    print_header("Testing Secure API")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Secure is running")
            print(f"  Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_result(False, f"Secure returned status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Cannot connect to Secure: {e}")
        print(f"  Make sure Secure is running: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False

def test_mydlp_status():
    """Test MyDLP status"""
    print_header("Testing MyDLP Status")
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            mydlp = data.get("mydlp", {})
            print_result(True, "MyDLP status check")
            print(f"  Enabled: {mydlp.get('enabled', False)}")
            print(f"  Status: {mydlp.get('status', 'unknown')}")
            print(f"  Localhost Mode: {mydlp.get('is_localhost', False)}")
            
            if not mydlp.get('enabled'):
                print("  ⚠ MyDLP is disabled (simulation mode)")
            elif not mydlp.get('is_localhost'):
                print("  ⚠ MyDLP is not in localhost mode")
            
            return True
        else:
            print_result(False, f"Status check returned {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error checking status: {e}")
        return False

def test_text_analysis():
    """Test text analysis"""
    print_header("Testing Text Analysis")
    try:
        test_text = "My name is John Doe and my phone is 123-456-7890. Email: test@example.com"
        response = requests.post(
            f"{BASE_URL}/api/analyze/",
            json={
                "text": test_text,
                "apply_policies": True,
                "source_ip": "127.0.0.1",
                "source_user": "test_user"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Text analysis working")
            entities = data.get('detected_entities', [])
            print(f"  Detected entities: {len(entities)}")
            for entity in entities:
                print(f"    - {entity.get('entity_type')}: {entity.get('value')} (confidence: {entity.get('score', 0):.2f})")
            print(f"  Blocked: {data.get('blocked', False)}")
            return True
        else:
            print_result(False, f"Analysis returned status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Analysis error: {e}")
        return False

def test_email_monitoring():
    """Test email monitoring"""
    print_header("Testing Email Monitoring")
    try:
        email_data = {
            "from": "employee@company.com",
            "to": ["customer@external.com"],
            "subject": "Customer Information",
            "body": "Dear Customer,\n\nYour account details:\nPhone: 123-456-7890\nCredit Card: 4532-1234-5678-9010\n\nBest regards",
            "source_ip": "127.0.0.1",
            "source_user": "employee@company.com"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/monitoring/email",
            json=email_data,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Email monitoring working")
            print(f"  Sensitive data detected: {data.get('sensitive_data_detected', False)}")
            print(f"  Action: {data.get('action', 'unknown')}")
            print(f"  Blocked: {data.get('blocked', False)}")
            
            entities = data.get('detected_entities', [])
            if entities:
                print(f"  Detected entities: {len(entities)}")
                for entity in entities:
                    print(f"    - {entity.get('entity_type')}: {entity.get('value')}")
            
            return True
        else:
            print_result(False, f"Email monitoring returned status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Email monitoring error: {e}")
        return False

def test_email_statistics():
    """Test email statistics"""
    print_header("Testing Email Statistics")
    try:
        response = requests.get(
            f"{BASE_URL}/api/monitoring/email/statistics?days=7",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Email statistics working")
            print(f"  Total emails analyzed: {data.get('total_emails_analyzed', 0)}")
            print(f"  Blocked emails: {data.get('blocked_emails', 0)}")
            print(f"  Allowed emails: {data.get('allowed_emails', 0)}")
            print(f"  Detected entities: {data.get('detected_entities', 0)}")
            return True
        else:
            print_result(False, f"Statistics returned status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Statistics error: {e}")
        return False

def test_network_monitoring():
    """Test network traffic monitoring"""
    print_header("Testing Network Traffic Monitoring")
    try:
        traffic_data = {
            "source_ip": "127.0.0.1",
            "destination": "external-server.com",
            "content": "User trying to send: My SSN is 123-45-6789",
            "protocol": "HTTPS"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/monitoring/traffic",
            json=traffic_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Network monitoring working")
            print(f"  Monitored: {data.get('monitored', False)}")
            return True
        else:
            print_result(False, f"Network monitoring returned status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Network monitoring error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Secure Local Setup Test")
    print("  Testing localhost configuration and email monitoring")
    print("=" * 60)
    
    results = []
    
    # Test 1: Secure Health
    results.append(("Secure Health", test_Secure_health()))
    
    # Test 2: MyDLP Status
    results.append(("MyDLP Status", test_mydlp_status()))
    
    # Test 3: Text Analysis
    results.append(("Text Analysis", test_text_analysis()))
    
    # Test 4: Email Monitoring
    results.append(("Email Monitoring", test_email_monitoring()))
    
    # Test 5: Email Statistics
    results.append(("Email Statistics", test_email_statistics()))
    
    # Test 6: Network Monitoring
    results.append(("Network Monitoring", test_network_monitoring()))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        print_result(result, name)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready for local monitoring.")
        print("\nNext steps:")
        print("  1. Open http://127.0.0.1:8000 in your browser")
        print("  2. Go to Monitoring tab to see email statistics")
        print("  3. Test email monitoring by sending test emails")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        if not results[0][1]:  # Secure not running
            print("\nTo start Secure:")
            print("  cd backend")
            print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return 1

if __name__ == "__main__":
    sys.exit(main())

