# دليل الاستخدام
# Usage Guide

## البدء السريع / Quick Start

### 1. تحليل نص بسيط

استخدم واجهة الويب:
1. افتح http://localhost:8000
2. اذهب إلى تبويب "تحليل النصوص"
3. أدخل النص المراد تحليله
4. اضغط "تحليل"

أو استخدم API:

```bash
curl -X POST http://localhost:8000/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My name is John Doe and my phone is 123-456-7890",
    "apply_policies": false
  }'
```

### 2. إنشاء سياسة

**من الواجهة:**
1. اذهب إلى تبويب "السياسات"
2. اضغط "سياسة جديدة"
3. املأ النموذج
4. اضغط "إنشاء"

**من API:**

```bash
curl -X POST http://localhost:8000/api/policies/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block Credit Cards",
    "entity_types": ["CREDIT_CARD"],
    "action": "block",
    "severity": "high",
    "enabled": true
  }'
```

### 3. عرض التنبيهات

**من الواجهة:**
1. اذهب إلى تبويب "التنبيهات"
2. اضغط "تحديث" لعرض أحدث التنبيهات

**من API:**

```bash
curl http://localhost:8000/api/alerts/
```

## سيناريوهات الاستخدام / Use Cases

### السيناريو 1: فحص ملف قبل الإرسال

```python
import requests

# تحليل النص
response = requests.post(
    "http://localhost:8000/api/analyze/",
    json={
        "text": "Content of file to be sent...",
        "apply_policies": True,
        "source_user": "user@example.com"
    }
)

result = response.json()

if result["blocked"]:
    print("⚠️ File contains sensitive data and was blocked!")
else:
    print("✓ File is safe to send")
```

### السيناريو 2: مراقبة حركة البيانات

```python
import requests

# مراقبة حركة البيانات
response = requests.post(
    "http://localhost:8000/api/monitoring/traffic",
    json={
        "source_ip": "192.168.1.100",
        "destination": "external",
        "content": "Data being transferred..."
    }
)

result = response.json()
print(f"Monitoring result: {result}")
```

### السيناريو 3: إنشاء سياسة GDPR

```python
import requests

# إنشاء سياسة متوافقة مع GDPR
response = requests.post(
    "http://localhost:8000/api/policies/",
    json={
        "name": "GDPR Personal Data Protection",
        "description": "Protect personal data according to GDPR",
        "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "ADDRESS"],
        "action": "encrypt",
        "severity": "high",
        "enabled": True,
        "gdpr_compliant": True
    }
)

policy = response.json()
print(f"Policy created: {policy['id']}")
```

### السيناريو 4: الحصول على تقرير أسبوعي

```python
import requests

# الحصول على تقرير آخر 7 أيام
response = requests.get(
    "http://localhost:8000/api/monitoring/reports/summary?days=7"
)

report = response.json()
print(f"Total alerts: {report['summary']['total_alerts']}")
print(f"Blocked attempts: {report['summary']['blocked_attempts']}")
```

## أمثلة متقدمة / Advanced Examples

### معالجة النصوص بالجملة

```python
import requests

texts = [
    "John Doe, phone: 123-456-7890",
    "Email: john@example.com",
    "Credit card: 4532-1234-5678-9010"
]

results = []
for text in texts:
    response = requests.post(
        "http://localhost:8000/api/analyze/",
        json={"text": text, "apply_policies": True}
    )
    results.append(response.json())

# معالجة النتائج
for i, result in enumerate(results):
    if result["sensitive_data_detected"]:
        print(f"Text {i+1}: {len(result['detected_entities'])} entities found")
```

### إدارة التنبيهات

```python
import requests

# الحصول على التنبيهات المعلقة
response = requests.get(
    "http://localhost:8000/api/alerts/?status=pending"
)
alerts = response.json()

# حل التنبيهات
for alert in alerts:
    if alert["severity"] == "low":
        requests.put(
            f"http://localhost:8000/api/alerts/{alert['id']}",
            json={"status": "resolved", "resolved_by": "admin"}
        )
```

## أفضل الممارسات / Best Practices

1. **استخدم السياسات بحكمة**: لا تفرط في إنشاء السياسات
2. **راقب التنبيهات بانتظام**: راجع التنبيهات يومياً
3. **راجع السجلات**: استخدم تقارير المراقبة لفهم الأنماط
4. **اختبر السياسات**: اختبر السياسات على بيانات تجريبية قبل التفعيل
5. **احفظ النسخ الاحتياطية**: احفظ قاعدة البيانات بانتظام

## التكامل مع أنظمة أخرى / Integration

### Python

```python
from app.services.policy_service import PolicyService
from app.database import get_db

db = next(get_db())
service = PolicyService()

result = service.apply_policy(
    db=db,
    text="Sensitive data here...",
    source_ip="192.168.1.1"
)
```

### REST API

استخدم أي مكتبة HTTP مثل:
- `requests` (Python)
- `axios` (JavaScript)
- `http` (Node.js)
- `curl` (Command line)

## الأمان / Security

1. **استخدم HTTPS في الإنتاج**
2. **احمِ مفاتيح التشفير**
3. **قلل الصلاحيات في قاعدة البيانات**
4. **راقب محاولات الوصول**
5. **حدث النظام بانتظام**

