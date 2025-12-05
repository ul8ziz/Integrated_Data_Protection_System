import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
DLP_API_URL = "http://127.0.0.1:8000/api/monitoring/email"

# Gmail Config (REPLACE WITH YOUR REAL DATA TO TEST)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password" # Get this from Google Account > Security > App Passwords

def send_secure_email(to_email, subject, body):
    print(f"\n📧 Attempting to send email to: {to_email}")
    
    # 1. CHECK WITH DLP SYSTEM FIRST
    print("🛡️  Checking with DLP System...")
    
    check_payload = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": subject,
        "body": body
    }
    
    try:
        response = requests.post(DLP_API_URL, json=check_payload)
        if response.status_code == 200:
            result = response.json()
            
            if result.get("blocked") is True:
                print(f"⛔ BLOCKED by DLP: {result.get('message')}")
                print("   ❌ Email was NOT sent to prevent data leak.")
                return False
            elif result.get("sensitive_data_detected"):
                print(f"⚠️  Warning: Sensitive data detected but allowed (Alert created).")
        else:
            print(f"⚠️  DLP Error ({response.status_code}). Proceeding with caution...")
            
    except Exception as e:
        print(f"⚠️  Could not connect to DLP: {e}")
        return False

    # 2. IF ALLOWED, SEND VIA REAL SMTP
    print("✅ DLP Check Passed. Sending via Gmail...")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if SENDER_PASSWORD == "your_app_password":
            print("❌ Error: You need to set SENDER_PASSWORD in the script to actually send.")
            return False

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        
        print("🚀 Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

if __name__ == "__main__":
    print("--- Real Email Integration Test ---")
    
    # Test Case 1: Clean Email
    # send_secure_email("friend@example.com", "Hello", "Just saying hi!")
    
    # Test Case 2: Leaking Data
    send_secure_email(
        "outsider@example.com", 
        "Secret Keys", 
        "Here is the credit card: 4532-1234-5678-9012"
    )

