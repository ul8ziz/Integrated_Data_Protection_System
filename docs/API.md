# وثائق API
# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

حالياً النظام لا يتطلب مصادقة. في الإنتاج يجب إضافة نظام مصادقة.

## Endpoints

### 1. تحليل النصوص / Text Analysis

#### POST /api/analyze/

تحليل نص لاكتشاف البيانات الحساسة.

**Request Body:**
```json
{
  "text": "My name is John Doe and my phone is 123-456-7890",
  "language": "en",
  "source_ip": "192.168.1.1",
  "source_user": "user@example.com",
  "source_device": "DESKTOP-123",
  "apply_policies": true
}
```

**Response:**
```json
{
  "sensitive_data_detected": true,
  "detected_entities": [
    {
      "entity_type": "PERSON",
      "start": 11,
      "end": 19,
      "score": 0.95,
      "value": "John Doe"
    },
    {
      "entity_type": "PHONE_NUMBER",
      "start": 38,
      "end": 50,
      "score": 0.98,
      "value": "123-456-7890"
    }
  ],
  "actions_taken": ["encrypted_PERSON", "blocked_by_policy_1"],
  "blocked": true,
  "alert_created": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

#### GET /api/analyze/entities

الحصول على قائمة أنواع الكيانات المدعومة.

**Response:**
```json
[
  "PERSON",
  "PHONE_NUMBER",
  "EMAIL_ADDRESS",
  "CREDIT_CARD",
  "ADDRESS",
  "ORGANIZATION"
]
```

### 2. إدارة السياسات / Policy Management

#### GET /api/policies/

الحصول على جميع السياسات.

**Query Parameters:**
- `enabled` (optional): true/false لتصفية حسب الحالة

**Response:**
```json
[
  {
    "id": 1,
    "name": "Block Credit Cards",
    "description": "Block all credit card numbers",
    "entity_types": ["CREDIT_CARD"],
    "action": "block",
    "severity": "high",
    "enabled": true,
    "apply_to_network": true,
    "apply_to_devices": true,
    "apply_to_storage": true,
    "gdpr_compliant": false,
    "hipaa_compliant": false,
    "created_at": "2024-01-01T12:00:00",
    "updated_at": null,
    "created_by": "admin"
  }
]
```

#### POST /api/policies/

إنشاء سياسة جديدة.

**Request Body:**
```json
{
  "name": "Block Credit Cards",
  "description": "Block all credit card numbers",
  "entity_types": ["CREDIT_CARD"],
  "action": "block",
  "severity": "high",
  "enabled": true,
  "apply_to_network": true,
  "apply_to_devices": true,
  "apply_to_storage": true,
  "gdpr_compliant": false,
  "hipaa_compliant": false,
  "created_by": "admin"
}
```

#### GET /api/policies/{policy_id}

الحصول على سياسة محددة.

#### PUT /api/policies/{policy_id}

تحديث سياسة.

#### DELETE /api/policies/{policy_id}

حذف سياسة.

### 3. التنبيهات / Alerts

#### GET /api/alerts/

الحصول على جميع التنبيهات.

**Query Parameters:**
- `status` (optional): pending, acknowledged, resolved, false_positive
- `severity` (optional): low, medium, high, critical
- `limit` (optional): عدد النتائج (default: 100)

#### GET /api/alerts/{alert_id}

الحصول على تنبيه محدد.

#### PUT /api/alerts/{alert_id}

تحديث حالة التنبيه.

**Request Body:**
```json
{
  "status": "resolved",
  "resolved_by": "admin"
}
```

#### GET /api/alerts/stats/summary

إحصائيات التنبيهات.

**Response:**
```json
{
  "total": 150,
  "pending": 25,
  "resolved": 120,
  "blocked": 50
}
```

### 4. المراقبة والتقارير / Monitoring & Reports

#### GET /api/monitoring/status

حالة النظام.

**Response:**
```json
{
  "status": "operational",
  "presidio": {
    "enabled": true,
    "status": "operational"
  },
  "mydlp": {
    "enabled": true,
    "status": "operational"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

#### POST /api/monitoring/traffic

مراقبة حركة البيانات.

**Request Body:**
```json
{
  "source_ip": "192.168.1.1",
  "destination": "external",
  "content": "text content here"
}
```

#### GET /api/monitoring/reports/summary

تقرير ملخص.

**Query Parameters:**
- `days` (optional): عدد الأيام (default: 7)

**Response:**
```json
{
  "period_days": 7,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-08T00:00:00",
  "summary": {
    "total_logs": 1000,
    "total_detected_entities": 250,
    "total_alerts": 50,
    "blocked_attempts": 20,
    "active_policies": 5
  },
  "entity_type_breakdown": {
    "PERSON": 100,
    "PHONE_NUMBER": 80,
    "CREDIT_CARD": 70
  }
}
```

#### GET /api/monitoring/reports/logs

تقرير السجلات.

**Query Parameters:**
- `event_type` (optional): نوع الحدث
- `level` (optional): مستوى السجل
- `limit` (optional): عدد النتائج (default: 100)

## أنواع الكيانات المدعومة / Supported Entity Types

- `PERSON`: أسماء الأشخاص
- `PHONE_NUMBER`: أرقام الهواتف
- `EMAIL_ADDRESS`: عناوين البريد الإلكتروني
- `CREDIT_CARD`: أرقام بطاقات الائتمان
- `ADDRESS`: العناوين
- `ORGANIZATION`: أسماء المنظمات
- `DATE_TIME`: التواريخ والأوقات
- `LOCATION`: المواقع الجغرافية
- `IBAN_CODE`: أرقام IBAN
- `IP_ADDRESS`: عناوين IP
- `MEDICAL_LICENSE`: تراخيص طبية
- `US_SSN`: أرقام الضمان الاجتماعي الأمريكي

## الإجراءات / Actions

- `block`: منع نقل البيانات
- `alert`: إنشاء تنبيه
- `encrypt`: تشفير البيانات
- `anonymize`: إخفاء الهوية

## مستويات الخطورة / Severity Levels

- `low`: منخفض
- `medium`: متوسط
- `high`: عالي
- `critical`: حرج

