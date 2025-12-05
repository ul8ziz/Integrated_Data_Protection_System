"""
Test script for sending real emails to the system
"""
import requests
import sys
import os
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def send_email_via_api(email_data):
    """Send email to the system via API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/email/receive",
            json=email_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"[ERROR] Server returned status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error sending email: {e}")
        return None


def main():
    print_header("Real Email Testing - Send Email to System")
    
    print("\nThis script demonstrates how to send real emails to the system.")
    print("You can use this method to integrate with:")
    print("  - SMTP proxies")
    print("  - Email gateways")
    print("  - Custom email handlers")
    print("  - Email forwarding services")
    
    # Example 1: Simple email
    print_header("Example 1: Sending Simple Email")
    
    email_data = {
        "from": "real.sender@example.com",
        "to": ["recipient@company.com"],
        "subject": "Test Email from Real Sender",
        "body": "This is a test email sent to the system.\n\nPhone: 555-1234-5678\nEmail: test@example.com",
        "source_ip": "192.168.1.100",
        "source_user": "real.sender@example.com"
    }
    
    print(f"\nSending email:")
    print(f"  From: {email_data['from']}")
    print(f"  To: {', '.join(email_data['to'])}")
    print(f"  Subject: {email_data['subject']}")
    
    result = send_email_via_api(email_data)
    
    if result:
        print(f"\n[OK] Email received and processed!")
        print(f"  Action: {result.get('action', 'N/A')}")
        print(f"  Blocked: {result.get('blocked', False)}")
        print(f"  Message: {result.get('message', 'N/A')}")
        
        analysis = result.get('analysis', {})
        if analysis.get('sensitive_data_detected'):
            print(f"\n  Sensitive data detected: {len(analysis.get('detected_entities', []))} entities")
            for entity in analysis.get('detected_entities', []):
                print(f"    - {entity.get('entity_type')}: {entity.get('value')}")
    else:
        print("\n[FAIL] Failed to send email")
    
    # Instructions
    print_header("How to Integrate with Real Email Systems")
    
    print("\n1. SMTP Proxy Integration:")
    print("   Configure your SMTP proxy to forward emails to:")
    print(f"   POST {API_BASE}/api/email/receive")
    print("   With JSON payload containing email data")
    
    print("\n2. Email Gateway Integration:")
    print("   Use the webhook URL in your email gateway settings:")
    print(f"   {API_BASE}/api/email/receive")
    
    print("\n3. Custom Script Integration:")
    print("   Use the requests library to send emails:")
    print("   ```python")
    print("   import requests")
    print("   requests.post('http://127.0.0.1:8000/api/email/receive', json={...})")
    print("   ```")
    
    print("\n4. Raw Email (RFC 2822) Format:")
    print(f"   POST {API_BASE}/api/email/receive/raw")
    print("   With raw email message in RFC 2822 format")
    
    print("\n5. Get Webhook Information:")
    print(f"   GET {API_BASE}/api/email/webhook/info")
    print("   Returns detailed information about endpoints")
    
    print("\n" + "=" * 70)
    print("For more information, check the API documentation:")
    print(f"  {API_BASE}/docs")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

