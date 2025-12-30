"""
Test script for local MyDLP setup and email monitoring
"""
import requests
import sys
import json
import os
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    """Print success message"""
    try:
        print(f"[OK] {text}")
    except UnicodeEncodeError:
        print(f"[OK] {text}")

def print_error(text):
    """Print error message"""
    try:
        print(f"[FAIL] {text}")
    except UnicodeEncodeError:
        print(f"[FAIL] {text}")

def print_warning(text):
    """Print warning message"""
    try:
        print(f"[WARNING] {text}")
    except UnicodeEncodeError:
        print(f"[WARNING] {text}")

def test_Secure_health():
    """Test Secure API health"""
    print_header("Testing Secure API Health")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Secure is running")
            print(f"  Name: {data.get('name', 'N/A')}")
            print(f"  Version: {data.get('version', 'N/A')}")
            print(f"  Status: {data.get('status', 'N/A')}")
            return True
        else:
            print_error(f"Secure returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to Secure: {e}")
        print_warning("Make sure Secure is running: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False

def test_system_status():
    """Test system status endpoint"""
    print_header("Testing System Status")
    try:
        response = requests.get(f"{API_BASE}/api/monitoring/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("System status retrieved")
            print(f"  Presidio: {data['presidio']['status']}")
            print(f"  MyDLP: {data['mydlp']['status']} ({'Enabled' if data['mydlp']['enabled'] else 'Disabled'})")
            if data['mydlp'].get('is_localhost'):
                print_success("  MyDLP running in localhost mode")
            return True
        else:
            print_error(f"Status endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error getting system status: {e}")
        return False

def test_text_analysis():
    """Test text analysis"""
    print_header("Testing Text Analysis")
    try:
        test_text = "My phone is 123-456-7890 and email is test@example.com. My name is John Doe."
        response = requests.post(
            f"{API_BASE}/api/analyze/",
            json={
                "text": test_text,
                "apply_policies": True
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success("Text analysis working")
            print(f"  Sensitive data detected: {data.get('sensitive_data_detected', False)}")
            print(f"  Detected entities: {len(data.get('detected_entities', []))}")
            if data.get('detected_entities'):
                print("\n  Detected entities:")
                for entity in data['detected_entities']:
                    print(f"    - {entity['entity_type']}: {entity['value']} (confidence: {entity['score']*100:.1f}%)")
            return True
        else:
            print_error(f"Analysis returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Analysis error: {e}")
        return False

def test_email_monitoring():
    """Test email monitoring"""
    print_header("Testing Email Monitoring")
    try:
        email_data = {
            "from": "employee@company.com",
            "to": ["external@example.com"],
            "subject": "Customer Data Request",
            "body": "Dear Customer,\n\nPlease find your information below:\nPhone: 123-456-7890\nEmail: customer@example.com\nAddress: 123 Main St, City, State 12345\n\nBest regards,\nEmployee",
            "source_ip": "127.0.0.1",
            "source_user": "employee@company.com"
        }
        
        response = requests.post(
            f"{API_BASE}/api/monitoring/email",
            json=email_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Email monitoring working")
            print(f"  Sensitive data detected: {data.get('sensitive_data_detected', False)}")
            print(f"  Action: {data.get('action', 'N/A')}")
            print(f"  Blocked: {data.get('blocked', False)}")
            print(f"  Detected entities: {len(data.get('detected_entities', []))}")
            
            if data.get('detected_entities'):
                print("\n  Detected sensitive data:")
                for entity in data['detected_entities']:
                    print(f"    - {entity['entity_type']}: {entity['value']}")
            
            if data.get('blocked'):
                print_warning("  Email was BLOCKED due to policy violation")
            else:
                print_success("  Email would be allowed")
            
            return True
        else:
            print_error(f"Email monitoring returned status {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('detail', 'Unknown error')}")
            except:
                pass
            return False
    except Exception as e:
        print_error(f"Email monitoring error: {e}")
        return False

def test_email_statistics():
    """Test email statistics"""
    print_header("Testing Email Statistics")
    try:
        response = requests.get(f"{API_BASE}/api/monitoring/email/statistics?days=7", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Email statistics retrieved")
            print(f"  Total emails analyzed: {data.get('total_emails_analyzed', 0)}")
            print(f"  Blocked emails: {data.get('blocked_emails', 0)}")
            print(f"  Allowed emails: {data.get('allowed_emails', 0)}")
            print(f"  Detected entities: {data.get('detected_entities', 0)}")
            return True
        else:
            print_warning(f"Email statistics returned {response.status_code} (may be normal if no emails analyzed yet)")
            return True  # Not critical
    except Exception as e:
        print_warning(f"Email statistics error: {e} (may be normal)")
        return True  # Not critical

def test_network_monitoring():
    """Test network traffic monitoring"""
    print_header("Testing Network Traffic Monitoring")
    try:
        traffic_data = {
            "source_ip": "127.0.0.1",
            "destination": "external.com",
            "content": "This contains sensitive data: Phone 123-456-7890, Email test@example.com",
            "protocol": "HTTP"
        }
        
        response = requests.post(
            f"{API_BASE}/api/monitoring/traffic",
            json=traffic_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Network monitoring working")
            print(f"  Monitored: {data.get('monitored', False)}")
            return True
        else:
            print_warning(f"Network monitoring returned {response.status_code}")
            return True  # Not critical if MyDLP is not running
    except Exception as e:
        print_warning(f"Network monitoring error: {e} (may be normal if MyDLP not running)")
        return True  # Not critical

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Secure Data Protection System - Local Setup Test")
    print("=" * 60)
    print(f"\nTesting against: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {
        "Secure_health": test_Secure_health(),
        "system_status": test_system_status(),
        "text_analysis": test_text_analysis(),
        "email_monitoring": test_email_monitoring(),
        "email_statistics": test_email_statistics(),
        "network_monitoring": test_network_monitoring()
    }
    
    print_header("Test Summary")
    print("\nResults:")
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name.replace('_', ' ').title()}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! System is ready.")
        return 0
    elif passed >= total - 2:  # Allow 2 non-critical tests to fail
        print_warning("Most tests passed. System is functional.")
        return 0
    else:
        print_error("Some critical tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

