# دليل تكامل الإيميلات الحقيقية
# Real Email Integration Guide

## نظرة عامة / Overview

هذا الدليل يشرح كيفية تكامل النظام مع إيميلات حقيقية من خوادم البريد الإلكتروني.

This guide explains how to integrate the system with real emails from email servers.

---

## الطرق المتاحة / Available Methods

### 1. JSON API Endpoint (الأسهل / Easiest)

**Endpoint**: `POST /api/email/receive`

**Payload Format**:
```json
{
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "subject": "Email subject",
  "body": "Email body text",
  "html_body": "<html>...</html>",  // optional
  "attachments": [  // optional
    {
      "filename": "file.pdf",
      "content": "base64_encoded_content"
    }
  ],
  "source_ip": "192.168.1.1",  // optional
  "source_user": "sender@example.com"  // optional
}
```

**Example using curl**:
```bash
curl -X POST http://127.0.0.1:8000/api/email/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from": "employee@company.com",
    "to": ["external@example.com"],
    "subject": "Customer Data",
    "body": "Phone: 123-456-7890, Email: customer@example.com"
  }'
```

**Example using Python**:
```python
import requests

email_data = {
    "from": "employee@company.com",
    "to": ["external@example.com"],
    "subject": "Customer Data",
    "body": "Phone: 123-456-7890, Email: customer@example.com"
}

response = requests.post(
    "http://127.0.0.1:8000/api/email/receive",
    json=email_data
)

result = response.json()
print(f"Action: {result['action']}")
print(f"Blocked: {result['blocked']}")
```

---

### 2. Raw Email (RFC 2822) Format

**Endpoint**: `POST /api/email/receive/raw`

**Content-Type**: `message/rfc822` or `text/plain`

**Example**:
```bash
curl -X POST http://127.0.0.1:8000/api/email/receive/raw \
  -H "Content-Type: message/rfc822" \
  --data-binary @email.eml
```

---

## التكامل مع أنظمة البريد / Email System Integration

### 1. SMTP Proxy Integration

#### استخدام Postfix (Linux)

إعداد Postfix لإعادة توجيه الإيميلات:

1. **تعديل `/etc/postfix/main.cf`**:
```conf
# Add custom transport
transport_maps = hash:/etc/postfix/transport
```

2. **إنشاء script لإعادة التوجيه**:
```bash
#!/bin/bash
# /usr/local/bin/forward_to_athier.sh

EMAIL_FILE="$1"
API_URL="http://127.0.0.1:8000/api/email/receive/raw"

curl -X POST "$API_URL" \
  -H "Content-Type: message/rfc822" \
  --data-binary @"$EMAIL_FILE"
```

3. **تعديل Postfix master.cf**:
```conf
athier unix - n n - - pipe
  flags=F user=nobody argv=/usr/local/bin/forward_to_athier.sh ${queue_directory}/${nexthop}
```

---

### 2. Email Gateway Integration

#### استخدام SendGrid Webhook

1. **إعداد Webhook في SendGrid**:
   - Go to Settings > Mail Settings > Event Webhook
   - Add webhook URL: `http://your-server:8000/api/email/receive`
   - Select events: "Inbound Parse"

2. **SendGrid سيرسل الإيميلات تلقائياً**:
```json
{
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "subject": "Subject",
  "text": "Body text",
  "html": "<html>Body</html>"
}
```

---

### 3. Microsoft 365 / Exchange Integration

#### استخدام Microsoft Graph API

```python
import requests
from msal import ConfidentialClientApplication

# Get access token
app = ConfidentialClientApplication(...)
token = app.acquire_token_for_client(...)

# Get emails from Microsoft 365
response = requests.get(
    "https://graph.microsoft.com/v1.0/me/messages",
    headers={"Authorization": f"Bearer {token['access_token']}"}
)

# Forward to Athier
for message in response.json()['value']:
    email_data = {
        "from": message['from']['emailAddress']['address'],
        "to": [msg['emailAddress']['address'] for msg in message['toRecipients']],
        "subject": message['subject'],
        "body": message['body']['content']
    }
    
    requests.post(
        "http://127.0.0.1:8000/api/email/receive",
        json=email_data
    )
```

---

### 4. Gmail Integration

#### استخدام Gmail API

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

# Authenticate
creds = Credentials.from_authorized_user_file('token.json')
service = build('gmail', 'v1', credentials=creds)

# Get messages
results = service.users().messages().list(userId='me').execute()
messages = results.get('messages', [])

for msg in messages:
    message = service.users().messages().get(userId='me', id=msg['id']).execute()
    
    # Extract email data
    headers = message['payload']['headers']
    from_email = next(h['value'] for h in headers if h['name'] == 'From')
    to_email = next(h['value'] for h in headers if h['name'] == 'To')
    subject = next(h['value'] for h in headers if h['name'] == 'Subject')
    
    # Get body
    body = message['payload']['body']['data']
    
    # Send to Athier
    email_data = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "body": body
    }
    
    requests.post(
        "http://127.0.0.1:8000/api/email/receive",
        json=email_data
    )
```

---

### 5. IMAP Integration

#### استخدام IMAP لمراقبة صندوق البريد

```python
import imaplib
import email
import requests

# Connect to IMAP server
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('user@gmail.com', 'password')
mail.select('inbox')

# Search for unread emails
status, messages = mail.search(None, 'UNSEEN')

for msg_num in messages[0].split():
    # Fetch email
    status, msg_data = mail.fetch(msg_num, '(RFC822)')
    email_body = msg_data[0][1]
    
    # Parse email
    msg = email.message_from_bytes(email_body)
    
    # Extract data
    from_email = msg['From']
    to_email = msg['To']
    subject = msg['Subject']
    body = msg.get_payload()
    
    # Send to Athier
    email_data = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "body": body
    }
    
    response = requests.post(
        "http://127.0.0.1:8000/api/email/receive",
        json=email_data
    )
    
    # Mark as read
    mail.store(msg_num, '+FLAGS', '\\Seen')
```

---

## اختبار التكامل / Testing Integration

### استخدام السكريبت التجريبي

```bash
cd backend
python test_real_email.py
```

### اختبار يدوي

```bash
# Test JSON endpoint
curl -X POST http://127.0.0.1:8000/api/email/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "to": ["recipient@example.com"],
    "subject": "Test",
    "body": "Test email body"
  }'

# Get webhook info
curl http://127.0.0.1:8000/api/email/webhook/info
```

---

## الأمان / Security

### 1. Authentication

لإنتاج حقيقي، أضف authentication:

```python
from fastapi import Depends, HTTPException, Header

async def verify_webhook_token(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@router.post("/receive")
async def receive_email(
    request: Request,
    api_key: str = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    # ... existing code
```

### 2. Rate Limiting

استخدم rate limiting لمنع الإساءة:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/receive")
@limiter.limit("10/minute")
async def receive_email(...):
    # ... existing code
```

---

## المراقبة / Monitoring

### عرض الإيميلات المستلمة

```bash
# Get email statistics
curl http://127.0.0.1:8000/api/monitoring/email/statistics

# Get email logs
curl http://127.0.0.1:8000/api/monitoring/email/logs?limit=50
```

### في الواجهة الويب

1. افتح `http://127.0.0.1:8000`
2. انتقل إلى تبويب **"Monitoring"**
3. شاهد إحصائيات الإيميلات
4. شاهد سجلات الإيميلات

---

## استكشاف الأخطاء / Troubleshooting

### المشكلة: الإيميلات لا تصل

**الحل**:
1. تحقق من أن الخادم يعمل: `http://127.0.0.1:8000/health`
2. تحقق من السجلات: `backend/logs/app.log`
3. اختبر الـ endpoint مباشرة باستخدام curl

### المشكلة: خطأ في التحليل

**الحل**:
1. تحقق من تنسيق البيانات
2. تأكد من أن الحقول المطلوبة موجودة
3. راجع السجلات للأخطاء

---

## أمثلة إضافية / Additional Examples

راجع ملف `backend/test_real_email.py` لأمثلة كاملة.

---

**آخر تحديث**: 2024

